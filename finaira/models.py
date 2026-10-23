from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Entity:
    type: str
    original_value: str
    start: int | None = None
    end: int | None = None
    entity_id: str | None = None
    language: str | None = None
    occurrence_index: int | None = None

    @classmethod
    def from_any(cls, value: "Entity | dict[str, Any]") -> "Entity":
        if isinstance(value, cls):
            return value
        data = dict(value)
        data["type"] = data.pop("entity_type", data.get("type"))
        data["original_value"] = data.pop("value", data.get("original_value"))
        data["start"] = data.pop("start", data.get("start_char"))
        data["end"] = data.pop("end", data.get("end_char"))
        data["entity_id"] = data.pop("id", data.get("entity_id"))
        return cls(**{k: data.get(k) for k in cls.__dataclass_fields__})


@dataclass
class PipelineRequest:
    document: str
    entities: list[Entity | dict[str, Any]]
    task: str = "Answer the user's task using the document."
    scope: str = "request"


@dataclass
class PipelineResult:
    status: str
    output: str | None = None
    sanitized_response: str | None = None
    error_code: str | None = None
    protected_document: str | None = None
    llm_request: dict[str, str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
