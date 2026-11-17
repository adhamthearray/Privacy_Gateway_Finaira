"""Document-level policy preparation for placeholder-based input.

The upstream detector is expected to send a document whose entity spans have
already been replaced with placeholders such as ``[[E0001]]``.  This module
does not call an LLM, choose a disclosure policy, or replace the document
text.  It returns a JSON-safe decision package containing either a
request-scoped pseudonymization form or the deterministic database candidates
that a later generalization selector may choose from.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from finaira_generalization import GeneralizationDB
from finaira_generalization.monetary import interpret_and_generalize_money

from .mapping import MappingVault
from .models import Entity
from .policy_config import PolicyConfig
from .policy import Action, canonical_entity_type, get_action


_DATABASE_INPUT_TYPES = {
    "COUNTRY",
    "NATIONALITY",
    "BANK",
    "CORPORATION",
    "ORGANIZATION",
    "UNIVERSITY",
    "GOVERNMENT_ENTITY",
    "JOB_TITLE",
    "OCCUPATION",
    "AGE",
    "DATE",
}

_MONETARY_OPTION_LEVELS = (
    ("RANGE_BASED", "range_based"),
    ("ORDER_OF_MAGNITUDE", "order_of_magnitude"),
    ("TASK_AWARE_THRESHOLD", "task_aware_threshold"),
)


def _input_language(value: str) -> str:
    return "ar" if any("\u0600" <= char <= "\u06ff" for char in value) else "en"


def _database_lookup_type(source_type: str) -> str:
    # BANK remains a useful source kind for the bank model-aware resolver;
    # the resolver itself exposes the result in the unified corporation domain.
    if source_type == "BANK":
        return "BANK"
    if source_type in {"ORGANIZATION", "UNIVERSITY"}:
        return "CORPORATION"
    return source_type


def _production_eligible(candidate: dict[str, Any]) -> bool:
    metadata = candidate.get("metadata") or {}
    provenance = candidate.get("provenance") or metadata.get("provenance") or {}
    if candidate.get("is_suppression", metadata.get("is_suppression", False)):
        return False
    if candidate.get("is_exact", metadata.get("is_exact", False)):
        return False
    if candidate.get("is_local_only", metadata.get("is_local_only", False)):
        return False
    if metadata.get("review_only") or provenance.get("requires_policy_approval"):
        return False
    if metadata.get("disclosure_approved") is False:
        return False
    if not candidate.get("available", True) or not candidate.get("representation"):
        return False
    return True


class DocumentSanitizer:
    """Prepare a placeholder document for deterministic sanitization.

    ``include_review_candidates`` defaults to ``True`` so the caller can see
    the complete review surface.  Every candidate carries a
    ``production_eligible`` flag; review-only and otherwise gated candidates
    are never silently promoted or selected.
    """

    def __init__(
        self,
        db_path: str | Path = "data/processed/finaira_generalization.db",
        *,
        include_review_candidates: bool = True,
        policy_config: PolicyConfig | dict[str, str] | None = None,
    ):
        self.db = GeneralizationDB(db_path)
        self.include_review_candidates = include_review_candidates
        self.policy_config = policy_config if isinstance(policy_config, PolicyConfig) else PolicyConfig(policy_config)

    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        document_id, text, entity_map = self._validate_request(request)
        vault = MappingVault()
        output_entities: dict[str, dict[str, Any]] = {}
        counts = {Action.PSEUDONYMIZE.value: 0, Action.GENERALIZE.value: 0, Action.ALLOW.value: 0}

        try:
            policy_overrides = request.get("policy_overrides") or {}
            if not isinstance(policy_overrides, dict):
                raise ValueError("POLICY_OVERRIDES_MUST_BE_OBJECT")
            for entity_id, supplied in entity_map.items():
                source_type = str(supplied["label"]).strip().upper()
                canonical_type = canonical_entity_type(source_type)
                action = self.policy_config.action_for(
                    source_type,
                    entity_id=entity_id,
                    supplied_action=supplied.get("policy_action"),
                    overrides=policy_overrides,
                )
                original_text = str(supplied["original_text"])
                placeholder = str(supplied["placeholder"])
                language = _input_language(original_text)
                entry: dict[str, Any] = {
                    "label": source_type,
                    "source_entity_type": source_type,
                    "canonical_entity_type": canonical_type,
                    "placeholder": placeholder,
                    "input_language": language,
                    "policy_action": action,
                    "effective_action": action,
                    "pseudonymization": None,
                    "pseudonymization_form": None,
                    "generalization": None,
                    "generalization_candidates": [],
                }

                if action == Action.PSEUDONYMIZE.value:
                    entity = Entity(canonical_type, original_text, entity_id=entity_id)
                    token = vault.token_for(entity, entity_id, action)
                    entry["pseudonymization"] = {
                        "form": token,
                        "reversible": True,
                        "scope": "document_request",
                    }
                    entry["pseudonymization_form"] = token
                elif action == Action.GENERALIZE.value:
                    package = self._generalization_package(
                        source_type,
                        canonical_type,
                        original_text,
                        language,
                        supplied,
                    )
                    has_replacement = package.pop("_has_production_replacement", False)
                    entry.update(package)
                    if not has_replacement:
                        entity = Entity(canonical_type, original_text, entity_id=entity_id)
                        token = vault.token_for(entity, entity_id, Action.PSEUDONYMIZE.value)
                        entry["effective_action"] = Action.PSEUDONYMIZE.value
                        entry["pseudonymization"] = {
                            "form": token,
                            "reversible": True,
                            "scope": "document_request",
                            "fallback_for": Action.GENERALIZE.value,
                        }
                        entry["pseudonymization_form"] = token
                        entry["fallback_reason"] = "NO_PRODUCTION_GENERALIZATION_CANDIDATE"

                counts[action] += 1
                output_entities[entity_id] = entry
        finally:
            vault.clear()

        return {
            "document_id": document_id,
            "text": text,
            "entities": output_entities,
            "policy_config": self.policy_config.to_dict(),
            "summary": {
                "pseudonymize_count": counts[Action.PSEUDONYMIZE.value],
                "generalize_count": counts[Action.GENERALIZE.value],
                "allow_count": counts[Action.ALLOW.value],
                "selection_performed": False,
            },
        }

    def _generalization_package(
        self,
        source_type: str,
        canonical_type: str,
        original_text: str,
        language: str,
        supplied: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if source_type == "MONETARY_AMOUNT":
            return self._monetary_package(original_text, supplied or {})
        if source_type not in _DATABASE_INPUT_TYPES:
            return {
                "generalization": {
                    "status": "NO_DATABASE_LOOKUP",
                    "resolution_status": None,
                    "canonical_id": None,
                    "requires_selection": False,
                }
            }

        lookup_type = _database_lookup_type(source_type)
        result = self.db.get_candidates(
            lookup_type,
            original_text,
            output_language=language,
            include_review_candidates=self.include_review_candidates,
            input_language=language,
        )
        candidates = []
        result_allows_production = result.get("resolution_status") in {"MATCHED", "VERIFIED"}
        for item in result.get("candidates", []):
            candidate = deepcopy(item)
            candidate["production_eligible"] = result_allows_production and _production_eligible(candidate)
            candidates.append(candidate)
        return {
            "generalization": {
                "status": result.get("resolution_status"),
                "reason_code": result.get("reason_code"),
                "canonical_id": result.get("canonical_id"),
                "runtime_entity_type": result.get("entity_type"),
                "requires_selection": bool(candidates),
                "selected_candidate": None,
            },
            "generalization_candidates": candidates,
            "_has_production_replacement": any(item["production_eligible"] for item in candidates),
        }

    @staticmethod
    def _monetary_package(original_text: str, supplied: dict[str, Any]) -> dict[str, Any]:
        context = supplied.get("monetary_context") or supplied.get("context") or {}
        if not isinstance(context, dict):
            raise ValueError("MONETARY_CONTEXT_MUST_BE_OBJECT")
        threshold_spec = supplied.get("threshold_spec")
        if threshold_spec is not None and not isinstance(threshold_spec, dict):
            raise ValueError("THRESHOLD_SPEC_MUST_BE_OBJECT")
        result = interpret_and_generalize_money(
            original_text,
            context=context,
            threshold_spec=threshold_spec,
        )
        candidates = []
        for rank, (level_code, key) in enumerate(_MONETARY_OPTION_LEVELS):
            option = dict(result["representations"].get(key) or {})
            status = option.get("status", "UNAVAILABLE")
            # An indeterminate comparison is informative but is not a
            # production-selectable representation.
            available = status in {"AVAILABLE", "TRUE", "FALSE"}
            candidates.append({
                "candidate_id": f"MONETARY_{level_code}",
                "level_code": level_code,
                "specificity_rank": rank,
                "representation": option.get("en"),
                "language": "bilingual",
                "taxonomy": "FINAIR_MONETARY",
                "taxonomy_code": level_code,
                "source": "Finaira monetary interpreter",
                "verification_status": "CONFIGURED",
                "metadata": {
                    "label_en": option.get("en"),
                    "label_ar": option.get("ar"),
                    "status": status,
                    "reason": option.get("reason"),
                    "is_exact": False,
                    "is_local_only": False,
                    "is_suppression": False,
                    "provenance": {"interpreter": "finaira_generalization.monetary"},
                },
                "available": available,
                "missing_reason": None if available else option.get("reason", status),
                "label_en": option.get("en"),
                "label_ar": option.get("ar"),
                "is_exact": False,
                "is_local_only": False,
                "is_suppression": False,
                "provenance": {"interpreter": "finaira_generalization.monetary"},
                "production_eligible": available,
            })
        interpretation = result.get("interpretation") or {}
        return {
            "generalization": {
                "status": interpretation.get("status"),
                "reason_code": interpretation.get("status"),
                "canonical_id": None,
                "runtime_entity_type": "MONETARY_AMOUNT",
                "requires_selection": any(item["production_eligible"] for item in candidates),
                "selected_candidate": None,
            },
            "monetary_result": result,
            "generalization_candidates": candidates,
            "_has_production_replacement": any(item["production_eligible"] for item in candidates),
        }

    @staticmethod
    def _validate_request(request: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        if not isinstance(request, dict):
            raise ValueError("REQUEST_MUST_BE_OBJECT")
        document_id = request.get("document_id")
        text = request.get("text")
        entity_map = request.get("entity_map")
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("DOCUMENT_ID_REQUIRED")
        if not isinstance(text, str):
            raise ValueError("DOCUMENT_TEXT_REQUIRED")
        if not isinstance(entity_map, dict):
            raise ValueError("ENTITY_MAP_REQUIRED")

        seen_placeholders: set[str] = set()
        for entity_id, supplied in entity_map.items():
            if not isinstance(entity_id, str) or not entity_id.strip():
                raise ValueError("ENTITY_ID_REQUIRED")
            if not isinstance(supplied, dict):
                raise ValueError(f"ENTITY_METADATA_MUST_BE_OBJECT:{entity_id}")
            for field in ("label", "original_text", "placeholder"):
                if not isinstance(supplied.get(field), str) or not supplied[field].strip():
                    raise ValueError(f"{field.upper()}_REQUIRED:{entity_id}")
            placeholder = supplied["placeholder"]
            if placeholder in seen_placeholders:
                raise ValueError(f"DUPLICATE_PLACEHOLDER:{placeholder}")
            seen_placeholders.add(placeholder)
            if placeholder not in text:
                raise ValueError(f"PLACEHOLDER_NOT_FOUND:{entity_id}")
            # Catch accidental map drift without requiring a particular ID
            # naming scheme such as E0001.
            if supplied["original_text"] == placeholder:
                raise ValueError(f"ORIGINAL_TEXT_EQUALS_PLACEHOLDER:{entity_id}")
        return document_id, text, entity_map


def prepare_document(
    request: dict[str, Any],
    db_path: str | Path = "data/processed/finaira_generalization.db",
    *,
    include_review_candidates: bool = True,
) -> dict[str, Any]:
    """Convenience wrapper returning a JSON-serializable decision package."""

    return DocumentSanitizer(
        db_path,
        include_review_candidates=include_review_candidates,
    ).prepare(request)

