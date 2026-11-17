"""Adapters between NER handoffs, policy decisions, and the JEV boundary."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .document_sanitizer import DocumentSanitizer
from .policy import Action
from .policy_config import PolicyConfig


JEV_PROTOCOL = "finaira-policy-to-jev-v1"


class NERPolicyJEVGateway:
    """Connect the NER document envelope to policy and a later JEV selector.

    This adapter never calls JEV.  It emits requests containing only eligible
    generalization candidates.  A downstream JEV integration can return a
    ``candidate_id`` and feed it to :meth:`apply_jev_selections`.
    """

    def __init__(
        self,
        db_path: str | Path = "data/processed/finaira_generalization.db",
        *,
        include_review_candidates: bool = True,
        policy_config: PolicyConfig | Mapping[str, str] | None = None,
    ):
        self.policy_config = policy_config if isinstance(policy_config, PolicyConfig) else PolicyConfig(policy_config)
        self.sanitizer = DocumentSanitizer(
            db_path,
            include_review_candidates=include_review_candidates,
            policy_config=self.policy_config,
        )

    def prepare(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Accept either one document or the NER batch envelope."""
        if "handoffs" in payload:
            return self.prepare_batch(payload)
        return self.sanitizer.prepare(payload)

    def prepare_batch(self, payload: dict[str, Any]) -> dict[str, Any]:
        handoffs = payload.get("handoffs")
        if not isinstance(handoffs, list):
            raise ValueError("HANDOFFS_MUST_BE_ARRAY")
        prepared = []
        jev_requests = []
        for document in handoffs:
            if not isinstance(document, dict):
                raise ValueError("HANDOFF_DOCUMENT_MUST_BE_OBJECT")
            result = self.sanitizer.prepare(document)
            prepared.append(result)
            jev_requests.extend(self._jev_requests(document, result))
        total = payload.get("total_documents", len(handoffs))
        if not isinstance(total, int) or total < len(handoffs):
            total = len(handoffs)
        return {
            "total_documents": total,
            "completed_documents": len(prepared),
            "handoffs": prepared,
            "policy_config": self.policy_config.to_dict(),
            "jev_handoff": {
                "protocol": JEV_PROTOCOL,
                "requests": jev_requests,
                "selection_contract": {
                    "selection_field": "candidate_id",
                    "allowed_candidate_rule": "candidate.production_eligible == true",
                    "no_selection_behavior": "retain pseudonymization fallback",
                    "selector_must_not_invent_candidates": True,
                },
            },
        }

    @staticmethod
    def _jev_requests(source: dict[str, Any], prepared: dict[str, Any]) -> list[dict[str, Any]]:
        requests = []
        for entity_id, supplied in source["entity_map"].items():
            entity = prepared["entities"][entity_id]
            candidates = [
                deepcopy(candidate)
                for candidate in entity.get("generalization_candidates", [])
                if candidate.get("production_eligible") is True
            ]
            if entity.get("policy_action") != Action.GENERALIZE.value or not candidates:
                continue
            requests.append({
                "request_id": f"{prepared['document_id']}:{entity_id}",
                "document_id": prepared["document_id"],
                "entity_id": entity_id,
                "entity_type": entity["canonical_entity_type"],
                "source_entity_type": entity["source_entity_type"],
                "input_language": entity["input_language"],
                "value": supplied["original_text"],
                "placeholder": supplied["placeholder"],
                "document": source["text"],
                "policy_action": entity["policy_action"],
                "candidates": candidates,
                "selected_candidate": None,
            })
        return requests

    @staticmethod
    def apply_jev_selections(
        prepared: dict[str, Any],
        selections: Mapping[str, Any] | list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Apply validated JEV candidate IDs without inventing replacements.

        Accepted selection shapes are either ``{"doc-id:E0001":
        "candidate-id"}``, ``{"doc-id": {"E0001": "candidate-id"}}``,
        or a list of records with ``document_id``, ``entity_id``, and
        ``candidate_id``.
        """
        result = deepcopy(prepared)
        normalized = NERPolicyJEVGateway._normalize_selections(selections)
        documents = result.get("handoffs") if isinstance(result.get("handoffs"), list) else [result]
        for document in documents:
            document_id = document.get("document_id")
            for entity_id, candidate_id in normalized:
                if document_id != entity_id[0]:
                    continue
                entity_key = entity_id[1]
                entity = document.get("entities", {}).get(entity_key)
                if entity is None:
                    raise ValueError(f"UNKNOWN_ENTITY:{document_id}:{entity_key}")
                candidates = entity.get("generalization_candidates", [])
                selected = next((item for item in candidates if item.get("candidate_id") == candidate_id), None)
                if selected is None or selected.get("production_eligible") is not True:
                    raise ValueError(f"INELIGIBLE_JEV_CANDIDATE:{candidate_id}")
                entity["effective_action"] = Action.GENERALIZE.value
                entity["pseudonymization"] = None
                entity["pseudonymization_form"] = None
                entity.pop("fallback_reason", None)
                entity["generalization"]["selected_candidate"] = deepcopy(selected)
                entity["generalization"]["selected_replacement"] = selected.get("representation")
                entity["jev_selection"] = {
                    "candidate_id": candidate_id,
                    "replacement": selected.get("representation"),
                }
                entity["generalization"]["requires_selection"] = False
            document.setdefault("summary", {})["selection_performed"] = any(
                item.get("jev_selection") for item in document.get("entities", {}).values()
            )
        if "jev_handoff" in result:
            result["jev_handoff"]["selections_applied"] = len(normalized)
        return result

    @staticmethod
    def _normalize_selections(selections: Mapping[str, Any] | list[dict[str, Any]]) -> list[tuple[tuple[str, str], str]]:
        pairs = []
        if isinstance(selections, list):
            for item in selections:
                if not isinstance(item, dict):
                    raise ValueError("JEV_SELECTION_MUST_BE_OBJECT")
                pairs.append(((str(item.get("document_id")), str(item.get("entity_id"))), str(item.get("candidate_id"))))
            return pairs
        if not isinstance(selections, Mapping):
            raise ValueError("JEV_SELECTIONS_MUST_BE_OBJECT_OR_ARRAY")
        for key, value in selections.items():
            if isinstance(value, Mapping):
                for entity_id, candidate_id in value.items():
                    pairs.append(((str(key), str(entity_id)), str(candidate_id)))
            else:
                document_id, separator, entity_id = str(key).partition(":")
                if not separator:
                    raise ValueError(f"JEV_SELECTION_KEY_MUST_BE_DOCUMENT_ENTITY:{key}")
                pairs.append(((document_id, entity_id), str(value)))
        return pairs


__all__ = ["JEV_PROTOCOL", "NERPolicyJEVGateway"]

