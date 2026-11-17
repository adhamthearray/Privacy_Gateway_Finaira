"""Configurable, validated privacy actions for integration boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .policy import Action, POLICY, canonical_entity_type, get_action


VALID_ACTIONS = {action.value for action in Action}


class PolicyConfig:
    """Resolve policy actions with optional per-request overrides.

    The default action table remains the repository policy.  A config file or
    request override can change an entity type, and a request override can
    target one entity ID.  Only the three existing actions are accepted.
    """

    def __init__(self, actions: Mapping[str, str] | None = None):
        self.actions = {key: action.value for key, action in POLICY.items()}
        if actions:
            self.actions.update(self._validated_actions(actions))

    @classmethod
    def from_file(cls, path: str | Path) -> "PolicyConfig":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("POLICY_CONFIG_MUST_BE_OBJECT")
        actions = payload.get("actions", payload)
        if not isinstance(actions, dict):
            raise ValueError("POLICY_ACTIONS_MUST_BE_OBJECT")
        return cls(actions)

    @staticmethod
    def _validated_actions(actions: Mapping[str, Any]) -> dict[str, str]:
        result = {}
        for entity_type, action in actions.items():
            key = str(entity_type).strip().upper()
            value = str(action).strip().upper()
            if value not in VALID_ACTIONS:
                raise ValueError(f"UNSUPPORTED_POLICY_ACTION:{value}")
            result[key] = value
        return result

    def action_for(
        self,
        entity_type: str,
        *,
        entity_id: str | None = None,
        supplied_action: str | None = None,
        overrides: Mapping[str, Any] | None = None,
    ) -> str:
        overrides = overrides or {}
        source = str(entity_type).strip().upper()
        canonical = canonical_entity_type(source)
        for key in (entity_id, source, canonical):
            if key and key in overrides:
                return self._validated_actions({key: overrides[key]})[key]
        if supplied_action is not None:
            return self._validated_actions({source: supplied_action})[source]
        if source in self.actions:
            return self.actions[source]
        if canonical in self.actions:
            return self.actions[canonical]
        return get_action(source).value

    def to_dict(self) -> dict[str, Any]:
        return {"version": "finaira-policy-actions-v1", "actions": dict(sorted(self.actions.items()))}

