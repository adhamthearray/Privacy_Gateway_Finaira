from types import SimpleNamespace
from unittest.mock import patch

import pytest
import torch

from model import MaskedLMCompletion, find_occurrences, replace_occurrence


def test_occurrence_selection_and_reconstruction():
    text = "Alice met Alice at the bank."
    assert find_occurrences(text, "Alice") == [0, 10]
    assert replace_occurrence(text, "Alice", "Mariam", 2) == "Alice met Mariam at the bank."


def test_missing_occurrence_is_rejected():
    with pytest.raises(ValueError, match="SELECTED_OCCURRENCE_NOT_FOUND"):
        replace_occurrence("Alice", "Alice", "Mariam", 2)


class _FakeTokenizer:
    mask_token = "[MASK]"
    mask_token_id = 99
    all_special_ids = [0, 99]

    def __call__(self, text, *, add_special_tokens=True, return_tensors=None, truncation=False, max_length=None):
        pieces = text.split()
        ids = [0] + [99 if piece == self.mask_token else 10 + (index % 5) for index, piece in enumerate(pieces)] + [0]
        if return_tensors == "pt":
            tensor = torch.tensor([ids], dtype=torch.long)
            return {"input_ids": tensor, "attention_mask": torch.ones_like(tensor)}
        return {"input_ids": ids[1:-1] if add_special_tokens is False else ids}

    def decode(self, ids, *, skip_special_tokens=True, clean_up_tokenization_spaces=True):
        return " ".join({10: "one", 11: "two", 12: "three", 13: "four", 14: "five"}.get(item, "token") for item in ids)


class _FakeMaskedLM:
    def to(self, device):
        return self

    def eval(self):
        return self

    def __call__(self, *, input_ids, attention_mask):
        batch, sequence = input_ids.shape
        logits = torch.full((batch, sequence, 20), -10.0)
        for row in range(batch):
            for position in range(sequence):
                logits[row, position, 10] = 5.0
                logits[row, position, 11] = 4.0
                logits[row, position, 12] = 3.0
        return SimpleNamespace(logits=logits)


def test_generate_returns_ranked_candidates_and_reconstructed_text():
    with patch("model.load_model", return_value=(_FakeTokenizer(), _FakeMaskedLM())):
        result = MaskedLMCompletion().generate(
            "Alice visited Cairo.",
            "Cairo.",
            "COUNTRY",
            model_name="fake-checkpoint",
            language="en",
            num_candidates=2,
            masking_mode="fixed",
            fixed_length=2,
            device="cpu",
        )

    assert result["model"]["official_ss_mtc"] is False
    assert result["masking"]["mask_count"] == 2
    assert len(result["candidates"]) == 2
    assert result["candidates"][0]["reconstructed_text"] != "Alice visited Cairo."
    assert "MODEL_OUTPUT_NOT_SEMANTICALLY_VALIDATED" in result["candidates"][0]["warnings"]


def test_generate_rejects_missing_span_before_model_load():
    with pytest.raises(ValueError, match="ENTITY_SPAN_NOT_FOUND"):
        MaskedLMCompletion().generate("Alice visited Cairo.", "Alexandria", "COUNTRY")

