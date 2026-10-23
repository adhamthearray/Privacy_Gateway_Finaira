from collections import defaultdict
from dataclasses import dataclass
from .models import Entity
from .policy import PREFIX


@dataclass
class MappingRecord:
    identity: str
    entity_type: str
    original: str
    sanitized: str
    action: str
    reversible: bool


class MappingVault:
    """Request-only map. It is deliberately not serializable or shared globally."""
    def __init__(self):
        self.by_identity: dict[str, MappingRecord] = {}
        self.by_token: dict[str, MappingRecord] = {}
        self.counters = defaultdict(int)

    def token_for(self, entity: Entity, identity: str, action: str) -> str:
        if identity in self.by_identity:
            return self.by_identity[identity].sanitized
        prefix = PREFIX.get(entity.type, entity.type)
        while True:
            self.counters[entity.type] += 1
            token = f"__FN_{prefix}_{self.counters[entity.type]:04d}__"
            if token not in self.by_token and token not in entity.original_value:
                break
        record = MappingRecord(identity, entity.type, entity.original_value, token, action, True)
        self.by_identity[identity] = record
        self.by_token[token] = record
        return token

    def record_generalization(self, entity: Entity, identity: str, value: str, action: str = "GENERALIZE"):
        if identity not in self.by_identity:
            self.by_identity[identity] = MappingRecord(identity, entity.type, entity.original_value, value, action, False)

    def clear(self):
        self.by_identity.clear(); self.by_token.clear(); self.counters.clear()

    def snapshot(self):
        return [
            {"identity": r.identity, "type": r.entity_type, "original": r.original,
             "sanitized": r.sanitized, "action": r.action, "reversible": r.reversible}
            for r in self.by_identity.values()
        ]
