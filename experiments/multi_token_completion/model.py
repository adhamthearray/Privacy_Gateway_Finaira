"""Local masked-language-model baseline for the MTC experiment playground.

This is deliberately separate from Finaira production code. It performs
multi-token beam completion by repeatedly filling mask positions with a local
masked language model. It is not SS-MTC and does not claim the paper's
expanded vocabulary or EMAT decoder.
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any

import torch


MODEL_CHOICES = [
    "bert-base-multilingual-cased",
    "bert-base-uncased",
]
ENTITY_TYPES = [
    "PERSON_NAME",
    "BANK",
    "CORPORATION",
    "GOVERNMENT_ENTITY",
    "OCCUPATION",
    "JOB_TITLE",
    "NATIONALITY",
    "COUNTRY",
    "AGE",
    "DATE",
    "OTHER",
]


@dataclass
class GenerationCandidate:
    rank: int
    replacement: str
    log_score: float
    reconstructed_text: str
    entity_type_consistency: str
    broader_than_original: str
    privacy_safety: str
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_device(requested: str) -> str:
    requested = (requested or "auto").lower()
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available")
        return "cuda"
    if requested == "cpu":
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=8)
def load_model(model_name: str, device: str):
    """Load and cache tokenizer/model pairs per checkpoint and device."""
    # Keep the experiment module lightweight for unit tests and UI construction.
    # Transformers imports optional scientific packages on some environments;
    # only pay that cost when a real model run is requested.
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForMaskedLM.from_pretrained(model_name)
    model.to(device)
    model.eval()
    if tokenizer.mask_token_id is None:
        raise RuntimeError(f"Checkpoint {model_name!r} does not expose a mask token")
    return tokenizer, model


def find_occurrences(text: str, span: str) -> list[int]:
    if not span:
        return []
    return [match.start() for match in re.finditer(re.escape(span), text)]


def replace_occurrence(text: str, span: str, replacement: str, occurrence: int) -> str:
    starts = find_occurrences(text, span)
    if not starts or occurrence < 1 or occurrence > len(starts):
        raise ValueError("SELECTED_OCCURRENCE_NOT_FOUND")
    start = starts[occurrence - 1]
    return text[:start] + replacement + text[start + len(span):]


def _candidate_warnings(original: str, replacement: str, entity_type: str) -> tuple[str, str, str, list[str]]:
    warnings = [
        "MODEL_OUTPUT_NOT_SEMANTICALLY_VALIDATED",
        "MODEL_SCORE_IS_NOT_PRIVACY_OR_UTILITY_CONFIDENCE",
    ]
    if not replacement.strip():
        warnings.append("EMPTY_REPLACEMENT")
    if replacement.casefold() == original.casefold():
        warnings.append("REPLACEMENT_EQUALS_ORIGINAL")
    if re.search(r"(?:https?://|www\.|@)", replacement):
        warnings.append("POTENTIAL_NEW_CONTACT_OR_URL")
    if re.search(r"\b\d{3}[-. ]\d{3}[-. ]\d{4}\b", replacement):
        warnings.append("POTENTIAL_NEW_PHONE_NUMBER")
    if re.search(r"\b(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", replacement):
        warnings.append("POTENTIAL_NEW_DATE")
    if replacement.casefold() in {"[unk]", "[mask]"}:
        warnings.append("SPECIAL_TOKEN_OUTPUT")
    return "NOT_VERIFIED", "NOT_VERIFIED", "NOT_ASSESSED", warnings


class MaskedLMCompletion:
    """Experimental local baseline with fixed/adaptive multi-mask generation."""

    method_name = "BASELINE_MASKED_LM_BEAM_SEARCH"
    official_ss_mtc = False

    def generate(
        self,
        document: str,
        span: str,
        entity_type: str,
        *,
        occurrence: int = 1,
        model_name: str = "bert-base-multilingual-cased",
        language: str = "auto",
        num_candidates: int = 5,
        masking_mode: str = "adaptive",
        fixed_length: int = 3,
        device: str = "auto",
        max_length: int = 4096,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        if not document.strip():
            raise ValueError("DOCUMENT_REQUIRED")
        if not span:
            raise ValueError("ENTITY_SPAN_REQUIRED")
        starts = find_occurrences(document, span)
        if not starts:
            raise ValueError("ENTITY_SPAN_NOT_FOUND")
        if occurrence < 1 or occurrence > len(starts):
            raise ValueError(f"OCCURRENCE_OUT_OF_RANGE:1-{len(starts)}")
        if not 1 <= int(num_candidates) <= 10:
            raise ValueError("NUM_CANDIDATES_MUST_BE_1_TO_10")
        if masking_mode not in {"fixed", "adaptive"}:
            raise ValueError("UNSUPPORTED_MASKING_MODE")
        if language not in {"auto", "en", "ar"}:
            raise ValueError("UNSUPPORTED_LANGUAGE_MODE")

        actual_device = resolve_device(device)
        tokenizer, model = load_model(model_name, actual_device)
        if tokenizer.mask_token is None:
            raise RuntimeError("MODEL_HAS_NO_MASK_TOKEN")
        if tokenizer.mask_token in document:
            raise ValueError("DOCUMENT_ALREADY_CONTAINS_MODEL_MASK_TOKEN")

        original_token_ids = tokenizer(span, add_special_tokens=False)["input_ids"]
        original_token_count = len(original_token_ids)
        if masking_mode == "adaptive":
            mask_count = max(1, min(original_token_count, 10))
        else:
            mask_count = max(1, min(int(fixed_length), 10))
        truncation_warning = None
        if original_token_count > 10 and masking_mode == "adaptive":
            truncation_warning = "ADAPTIVE_MASK_LENGTH_CAPPED_AT_10"

        mask_text = " ".join([tokenizer.mask_token] * mask_count)
        start = starts[occurrence - 1]
        masked_document = document[:start] + mask_text + document[start + len(span):]
        encoded = tokenizer(
            masked_document,
            return_tensors="pt",
            truncation=True,
            max_length=max_length,
        )
        input_ids = encoded["input_ids"][0]
        mask_positions = (input_ids == tokenizer.mask_token_id).nonzero(as_tuple=False).flatten().tolist()
        if len(mask_positions) != mask_count:
            raise ValueError("MASKED_SPAN_TRUNCATED_OR_NOT_TOKENIZED")

        beams: list[tuple[torch.Tensor, list[int], float]] = [(input_ids, [], 0.0)]
        beam_width = max(int(num_candidates) * 2, 4)
        special_ids = set(tokenizer.all_special_ids)
        with torch.inference_mode():
            for _ in range(mask_count):
                expanded: list[tuple[torch.Tensor, list[int], float]] = []
                ids_batch = torch.stack([item[0] for item in beams]).to(actual_device)
                model_inputs = {}
                for key, value in encoded.items():
                    value = value.to(actual_device)
                    model_inputs[key] = value if key == "input_ids" else value.expand(len(beams), -1)
                model_inputs["input_ids"] = ids_batch
                logits = model(**model_inputs).logits
                for beam_index, (ids, generated_ids, score) in enumerate(beams):
                    position = next((pos for pos in mask_positions if int(ids[pos]) == tokenizer.mask_token_id), None)
                    if position is None:
                        continue
                    log_probs = torch.log_softmax(logits[beam_index, position], dim=-1)
                    values, indices = torch.topk(log_probs, k=min(beam_width, log_probs.shape[-1]))
                    for value, index in zip(values.tolist(), indices.tolist()):
                        if index in special_ids or index == tokenizer.mask_token_id:
                            continue
                        next_ids = ids.clone()
                        next_ids[position] = index
                        expanded.append((next_ids, generated_ids + [index], score + float(value)))
                if not expanded:
                    raise RuntimeError("MODEL_GENERATED_NO_VALID_TOKEN")
                expanded.sort(key=lambda item: item[2], reverse=True)
                beams = expanded[:beam_width]

        candidates: list[GenerationCandidate] = []
        seen: set[str] = set()
        for ids, generated_ids, score in sorted(beams, key=lambda item: item[2], reverse=True):
            replacement = tokenizer.decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            ).strip()
            if not replacement or replacement in seen or replacement.casefold() == span.casefold():
                continue
            seen.add(replacement)
            warnings = []
            if truncation_warning:
                warnings.append(truncation_warning)
            consistency, broader, privacy, model_warnings = _candidate_warnings(span, replacement, entity_type)
            warnings.extend(model_warnings)
            candidates.append(GenerationCandidate(
                rank=len(candidates) + 1,
                replacement=replacement,
                log_score=round(score, 6),
                reconstructed_text=replace_occurrence(document, span, replacement, occurrence),
                entity_type_consistency=consistency,
                broader_than_original=broader,
                privacy_safety=privacy,
                warnings=warnings,
            ))
            if len(candidates) >= int(num_candidates):
                break

        if not candidates:
            raise RuntimeError("MODEL_RETURNED_NO_DISTINCT_CANDIDATES")
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "document": document,
            "masked_document": masked_document,
            "selected_span": span,
            "entity_type": entity_type,
            "occurrence": occurrence,
            "occurrence_count": len(starts),
            "language_mode": language,
            "model": {
                "requested_checkpoint": model_name,
                "loaded_checkpoint": model_name,
                "device": actual_device,
                "method": self.method_name,
                "official_ss_mtc": self.official_ss_mtc,
                "baseline_notice": "This is ordinary masked-LM beam completion, not SS-MTC.",
            },
            "masking": {
                "mode": masking_mode,
                "mask_count": mask_count,
                "original_token_count": original_token_count,
                "fixed_length": int(fixed_length),
            },
            "latency_ms": elapsed_ms,
            "score_notice": "Log scores rank model outputs only; they are not privacy or utility confidence.",
            "candidates": [candidate.to_dict() for candidate in candidates],
        }


__all__ = [
    "ENTITY_TYPES",
    "MODEL_CHOICES",
    "GenerationCandidate",
    "MaskedLMCompletion",
    "find_occurrences",
    "load_model",
    "replace_occurrence",
]

