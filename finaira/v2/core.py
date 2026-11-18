"""Deterministic, task-aware V2 optimization over Finaira candidates.

The production path is deliberately strict:

* policy must say GENERALIZE for every optimized entity;
* database-backed examples require a MATCHED/VERIFIED exact lookup;
* exact/raw candidates, review-only candidates, suppressed candidates and
  local-only candidates are never selectable;
* a typed numbered pseudonym is pre-reserved before any optimizer runs.

The only exception is ``make_golden_fixture``. The task specification requires
one fixed synthetic fixture with fixed U/S values; it is marked synthetic and
is never used by the production example builder.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import re
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from ..mapping import MappingVault
from ..policy import PREFIX, Action, canonical_entity_type, get_action
from ..policy_config import PolicyConfig
from finaira_generalization import GeneralizationDB
from finaira_generalization.monetary import interpret_and_generalize_money


GENERALIZABLE_TYPES = {
    "AGE", "DATE", "MONETARY_AMOUNT", "BANK", "CORPORATION",
    "ORGANIZATION", "UNIVERSITY", "GOVERNMENT_ENTITY", "COUNTRY",
    "NATIONALITY", "JOB_TITLE", "OCCUPATION",
}
DATABASE_TYPES = GENERALIZABLE_TYPES - {"MONETARY_AMOUNT"}
PRODUCTION_STATUSES = {"MATCHED", "VERIFIED"}
PSEUDONYM_RE = re.compile(r"__FN_([A-Z0-9_]+)_(\d{4})__")


def _norm(value: str) -> str:
    return unicodedata.normalize("NFKC", str(value)).casefold().strip()


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)


@dataclass
class Candidate:
    entity_id: str
    entity_type: str
    text: str
    transformation: str
    utility_loss: float | None
    specificity: float | None
    hierarchy_node: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    preserves_mandatory: bool = True
    terminal_pseudonym: bool = False
    forbidden_original: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "candidate_id": self.metadata.get("candidate_id"),
            "text": self.text,
            "transformation": self.transformation,
            "utility_loss": self.utility_loss,
            "specificity": self.specificity,
            "hierarchy_node": self.hierarchy_node,
            "source": self.source,
            "metadata": _jsonable(self.metadata),
            "preserves_mandatory": self.preserves_mandatory,
            "terminal_pseudonym": self.terminal_pseudonym,
            "forbidden_original": self.forbidden_original,
        }


@dataclass
class EntitySpec:
    entity_id: str
    entity_type: str
    original: str
    language: str = "en"
    start: int | None = None
    end: int | None = None
    identity_key: str | None = None
    canonical_id: str | None = None
    source_entity_type: str | None = None
    candidates: list[Candidate] = field(default_factory=list)
    lookup: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EntitySpec":
        source_type = str(value.get("source_entity_type") or value.get("type") or value.get("entity_type") or "").upper()
        entity_type = canonical_entity_type(source_type)
        original = str(value.get("original", value.get("original_text", value.get("value", ""))))
        if not source_type or not original:
            raise ValueError("ENTITY_ID_TYPE_AND_ORIGINAL_REQUIRED")
        return cls(
            entity_id=str(value.get("id", value.get("entity_id", ""))),
            entity_type=entity_type,
            original=original,
            language=str(value.get("language") or ("ar" if re.search(r"[\u0600-\u06ff]", original) else "en")),
            start=value.get("start", value.get("start_char")),
            end=value.get("end", value.get("end_char")),
            identity_key=value.get("identity_key"),
            canonical_id=value.get("canonical_id"),
            source_entity_type=source_type,
            metadata=dict(value.get("metadata") or {}),
        )


@dataclass(frozen=True)
class TaskProfile:
    task_id: str
    mandatory_facts: tuple[str, ...] = ()
    optional_facts: tuple[str, ...] = ()
    precision_requirements: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationTargets:
    max_task_accuracy_drop_pp: float = 2.0
    min_specificity_reduction_pct: float = 20.0
    require_mandatory_fact_preservation: bool = True
    require_policy_compliance: bool = True
    latency_budget_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OptimizationRequest:
    case_id: str
    task: str
    document: str
    entities: list[EntitySpec]
    explicit_requirements: dict[str, Any] = field(default_factory=dict)
    synthetic_fixture: bool = False

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OptimizationRequest":
        entities = [EntitySpec.from_dict(item) for item in value.get("entities", [])]
        for index, entity in enumerate(entities, start=1):
            if not entity.entity_id:
                entity.entity_id = f"e{index}"
        return cls(
            case_id=str(value.get("case_id") or value.get("scope") or "case-default"),
            task=str(value.get("task") or value.get("task_id") or ""),
            document=str(value.get("document") or ""),
            entities=entities,
            explicit_requirements=dict(value.get("requirements") or {}),
            synthetic_fixture=bool(value.get("synthetic_fixture", False)),
        )


TASK_PROFILES: dict[str, TaskProfile] = {
    "professional_summary": TaskProfile(
        "professional_summary", ("meaningful_professional_category",),
        ("specific_job_detail",), {},
    ),
    "customer_demographic_summary": TaskProfile(
        "customer_demographic_summary", ("demographic_category",), (), {},
    ),
    "age_eligibility": TaskProfile(
        "age_eligibility", ("age_threshold",), (), {"threshold": 21},
    ),
    "nationality_country_eligibility": TaskProfile(
        "nationality_country_eligibility", ("required_country_or_nationality",), (), {},
    ),
    "financial_field_extraction": TaskProfile(
        "financial_field_extraction", ("amount_currency_and_unit",), (), {},
    ),
    "financial_transaction_summary": TaskProfile(
        "financial_transaction_summary", ("amount_currency_and_association",), (), {},
    ),
}


def resolve_task_profile(task: str, explicit: Mapping[str, Any] | None = None) -> TaskProfile | None:
    key = _norm(task).replace(" ", "_")
    aliases = {
        "summarize_the_customer_s_professional_background": "professional_summary",
        "summarize_the_customer's_professional_background": "professional_summary",
        "professional_background": "professional_summary",
        "demographic_summary": "customer_demographic_summary",
        "age_eligibility": "age_eligibility",
        "nationality_eligibility": "nationality_country_eligibility",
        "country_eligibility": "nationality_country_eligibility",
        "financial_extraction": "financial_field_extraction",
        "transaction_summary": "financial_transaction_summary",
    }
    key = aliases.get(key, key)
    if key in TASK_PROFILES:
        profile = TASK_PROFILES[key]
        if explicit:
            return TaskProfile(
                profile.task_id,
                tuple(explicit.get("mandatory_facts", profile.mandatory_facts)),
                tuple(explicit.get("optional_facts", profile.optional_facts)),
                dict(explicit.get("precision_requirements", profile.precision_requirements)),
            )
        return profile
    if explicit and explicit.get("mandatory_facts") is not None:
        return TaskProfile(key or "explicit", tuple(explicit.get("mandatory_facts", ())), tuple(explicit.get("optional_facts", ())), dict(explicit.get("precision_requirements", {})))
    return None


class CaseScopedPseudonymizer:
    """Stable, case-local typed placeholders reserved before selection."""

    def __init__(self, case_id: str, state: dict[str, Any] | None = None, existing_document: str = ""):
        self.case_id = case_id
        self.state = state if state is not None else {"mappings": {}, "counters": {}}
        self.state.setdefault("mappings", {})
        self.state.setdefault("counters", {})
        self.used_tokens = {match.group(0) for match in PSEUDONYM_RE.finditer(existing_document)}
        for match in PSEUDONYM_RE.finditer(existing_document):
            prefix, index = match.groups()
            self.state["counters"][prefix] = max(int(index), int(self.state["counters"].get(prefix, 0)))

    @staticmethod
    def _prefix(entity_type: str) -> str:
        return PREFIX.get(entity_type, entity_type)

    def reserve(self, entity: EntitySpec) -> str:
        key = entity.identity_key or entity.canonical_id or entity.entity_id
        map_key = f"{canonical_entity_type(entity.entity_type)}:{key}"
        if map_key in self.state["mappings"]:
            return self.state["mappings"][map_key]
        prefix = self._prefix(entity.entity_type)
        next_index = int(self.state["counters"].get(prefix, 0))
        while True:
            next_index += 1
            token = f"__FN_{prefix}_{next_index:04d}__"
            if token not in self.used_tokens and token not in self.state["mappings"].values():
                break
        self.state["counters"][prefix] = next_index
        self.state["mappings"][map_key] = token
        self.used_tokens.add(token)
        return token

    def reserve_all(self, entities: Iterable[EntitySpec]) -> dict[str, str]:
        return {entity.entity_id: self.reserve(entity) for entity in entities}

    def snapshot(self) -> dict[str, Any]:
        return {"case_id": self.case_id, "mappings": dict(self.state["mappings"]), "counters": dict(self.state["counters"])}


def _candidate_eligible(candidate: Mapping[str, Any], original: str) -> bool:
    meta = candidate.get("metadata") or {}
    provenance = candidate.get("provenance") or meta.get("provenance") or {}
    text = candidate.get("representation") or candidate.get("text")
    if not text or _norm(text) == _norm(original):
        return False
    if candidate.get("is_exact", meta.get("is_exact", False)):
        return False
    if candidate.get("is_suppression", meta.get("is_suppression", False)):
        return False
    if candidate.get("is_local_only", meta.get("is_local_only", False)):
        return False
    if meta.get("review_only") or provenance.get("requires_policy_approval"):
        return False
    if meta.get("disclosure_approved") is False or candidate.get("available") is False:
        return False
    return True


def _specificity_for(candidate: Mapping[str, Any], max_rank: int) -> tuple[float | None, str, dict[str, Any]]:
    meta = dict(candidate.get("metadata") or {})
    if meta.get("specificity") is not None:
        return float(meta["specificity"]), "configured_fixture", {"method": "configured_fixture", "specificity": float(meta["specificity"])}
    domain = meta.get("reference_domain_size")
    compatible = meta.get("compatible_atomic_values")
    if domain and compatible and float(domain) > 1 and 0 < float(compatible) <= float(domain):
        score = math.log(float(domain) / float(compatible)) / math.log(float(domain))
        return max(0.0, min(1.0, score)), "domain_coverage", {"method": "domain_coverage", "reference_domain_size": domain, "compatible_atomic_values": compatible}
    rank = candidate.get("specificity_rank", meta.get("specificity_rank"))
    if rank is not None and max_rank > 0:
        distance = float(rank)
        score = max(0.0, min(1.0, 1.0 - distance / float(max_rank)))
        return score, "hierarchy_distance_fallback", {"method": "hierarchy_distance_fallback", "distance": distance, "root_distance": max_rank, "warning": "Structural hierarchy fallback; not population frequency."}
    return None, "unavailable", {"method": "unavailable", "reason": "NO_DOMAIN_OR_TRUSTWORTHY_HIERARCHY"}


def _age_bounds(text: str) -> tuple[int | None, int | None]:
    nums = [int(item) for item in re.findall(r"\d+", str(text))]
    if not nums:
        return None, None
    return (nums[0], nums[-1] if len(nums) > 1 else nums[0])


def _preserves(entity: EntitySpec, candidate_text: str, candidate_meta: Mapping[str, Any], profile: TaskProfile, terminal: bool) -> bool:
    if terminal:
        if profile.task_id == "professional_summary":
            return entity.entity_type not in {"JOB_TITLE", "OCCUPATION"}
        if profile.task_id == "age_eligibility":
            return entity.entity_type != "AGE"
        if profile.task_id == "nationality_country_eligibility":
            return entity.entity_type not in {"COUNTRY", "NATIONALITY"}
        if profile.task_id == "customer_demographic_summary":
            return entity.entity_type not in {"AGE", "COUNTRY", "NATIONALITY"}
        if profile.task_id in {"financial_field_extraction", "financial_transaction_summary"}:
            return entity.entity_type != "MONETARY_AMOUNT"
        return True
    facts = set(candidate_meta.get("preserves_facts", ()))
    if facts:
        return all(fact in facts for fact in profile.mandatory_facts)
    task = profile.task_id
    if not profile.mandatory_facts:
        return True
    if task == "professional_summary" and entity.entity_type in {"JOB_TITLE", "OCCUPATION"}:
        return str(candidate_meta.get("level_code", "")).startswith("ISCO_")
    if task == "professional_summary":
        return True
    if task == "age_eligibility" and entity.entity_type == "AGE":
        threshold = int(profile.precision_requirements.get("threshold", 21))
        low, high = _age_bounds(candidate_text)
        return low is not None and low >= threshold
    if task == "nationality_country_eligibility" and entity.entity_type in {"COUNTRY", "NATIONALITY"}:
        target = _norm(str(profile.precision_requirements.get("required_code", "")))
        return bool(target and target in {_norm(str(candidate_meta.get("canonical_id", ""))), _norm(str(candidate_meta.get("country_code", "")))})
    if task in {"financial_field_extraction", "financial_transaction_summary"} and entity.entity_type == "MONETARY_AMOUNT":
        return bool(candidate_meta.get("currency") or candidate_meta.get("unit") or candidate_meta.get("preserves_facts"))
    if task == "customer_demographic_summary" and entity.entity_type in {"AGE", "COUNTRY", "NATIONALITY"}:
        return True
    if task == "customer_demographic_summary":
        return True
    return False


class V2Optimizer:
    """Build policy-valid candidates and compare V1, greedy and MILP V2."""

    def __init__(self, db_path: str | Path = "data/processed/finaira_generalization.db", *, policy_config: PolicyConfig | None = None):
        self.db = GeneralizationDB(db_path)
        self.db_path = str(db_path)
        self.policy_config = policy_config or PolicyConfig()
        self._lookup_cache: dict[tuple[str, str, str], dict[str, Any]] = {}

    def _db_lookup(self, entity_type: str, value: str, language: str) -> dict[str, Any]:
        key = (entity_type, value, language)
        if key not in self._lookup_cache:
            self._lookup_cache[key] = self.db.get_candidates(entity_type, value, output_language=language, include_review_candidates=False, input_language=language)
        return self._lookup_cache[key]

    def prepare(self, request: OptimizationRequest | Mapping[str, Any], *, pseudonym_state: dict[str, Any] | None = None) -> tuple[OptimizationRequest, TaskProfile, dict[str, str]]:
        if not isinstance(request, OptimizationRequest):
            request = OptimizationRequest.from_dict(request)
        if not request.document:
            raise ValueError("DOCUMENT_REQUIRED")
        profile = resolve_task_profile(request.task, request.explicit_requirements)
        if profile is None:
            raise ValueError("UNKNOWN_TASK_REQUIREMENTS")
        if not request.entities:
            raise ValueError("GENERALIZABLE_ENTITIES_REQUIRED")
        for entity in request.entities:
            if entity.entity_type not in GENERALIZABLE_TYPES and not (request.synthetic_fixture and entity.entity_type == "LOCATION"):
                raise ValueError(f"UNSUPPORTED_V2_ENTITY_TYPE:{entity.entity_type}")
            if not (request.synthetic_fixture and entity.entity_type == "LOCATION"):
                self._preload_identity(entity)
                action = self.policy_config.action_for(entity.source_entity_type or entity.entity_type)
            else:
                action = Action.GENERALIZE.value
            if action != Action.GENERALIZE.value:
                raise ValueError(f"ENTITY_NOT_POLICY_GENERALIZABLE:{entity.entity_id}:{entity.entity_type}:{action}")
        pseudonyms = CaseScopedPseudonymizer(request.case_id, pseudonym_state, request.document)
        token_map = pseudonyms.reserve_all(request.entities)
        for entity in request.entities:
            self._build_candidates(entity, profile, token_map[entity.entity_id], synthetic=request.synthetic_fixture)
        return request, profile, token_map

    def _preload_identity(self, entity: EntitySpec) -> None:
        """Use one unique exact/direct DB identity for repeated mentions."""
        if entity.identity_key or entity.entity_type not in DATABASE_TYPES:
            return
        lookup_type = "CORPORATION" if entity.entity_type in {"ORGANIZATION", "UNIVERSITY"} else entity.entity_type
        result = self._db_lookup(lookup_type, entity.original, entity.language)
        exact = [item for item in result.get("candidates", []) if item.get("is_exact") and not item.get("is_suppression")]
        if result.get("resolution_status") in PRODUCTION_STATUSES and len(exact) == 1 and result.get("canonical_id"):
            entity.canonical_id = entity.canonical_id or result.get("canonical_id")
            entity.identity_key = entity.identity_key or entity.canonical_id

    def _build_candidates(self, entity: EntitySpec, profile: TaskProfile, pseudonym: str, *, synthetic: bool) -> None:
        if synthetic:
            raw = entity.metadata.get("synthetic_candidates") or []
            entity.candidates = [self._candidate_from_raw(entity, item, profile, pseudonym) for item in raw]
            return
        raw_candidates: list[dict[str, Any]] = []
        lookup: dict[str, Any] = {"mode": "database_exact_direct", "input": entity.original}
        if entity.entity_type == "MONETARY_AMOUNT":
            money = interpret_and_generalize_money(entity.original, context=entity.metadata.get("context") or {}, threshold_spec=entity.metadata.get("threshold_spec"))
            lookup = {"mode": "configured_deterministic_interpreter", "status": money.get("interpretation", {}).get("status")}
            for rank, (level, key) in enumerate((("RANGE_BASED", "range_based"), ("ORDER_OF_MAGNITUDE", "order_of_magnitude"), ("TASK_AWARE_THRESHOLD", "task_aware_threshold"))):
                option = money.get("representations", {}).get(key) or {}
                raw_candidates.append({"candidate_id": f"MONETARY_{level}", "level_code": level, "representation": option.get("en"), "specificity_rank": rank + 1, "source": "Finaira monetary interpreter", "verification_status": "CONFIGURED", "metadata": {"label_en": option.get("en"), "label_ar": option.get("ar"), "status": option.get("status"), "preserves_facts": ("amount_currency_and_unit",) if option.get("status") == "AVAILABLE" else ()}})
        elif entity.entity_type in DATABASE_TYPES:
            lookup_type = "CORPORATION" if entity.entity_type in {"ORGANIZATION", "UNIVERSITY"} else entity.entity_type
            result = self._db_lookup(lookup_type, entity.original, entity.language)
            lookup.update({"resolution_status": result.get("resolution_status"), "reason_code": result.get("reason_code"), "canonical_id": result.get("canonical_id"), "entity_type": result.get("entity_type")})
            entity.canonical_id = entity.canonical_id or result.get("canonical_id")
            exact = [item for item in result.get("candidates", []) if item.get("is_exact") and not item.get("is_suppression")]
            lookup["direct_match"] = bool(exact)
            if result.get("resolution_status") in PRODUCTION_STATUSES and exact:
                raw_candidates = list(result.get("candidates", []))
        entity.lookup = lookup
        eligible = [item for item in raw_candidates if _candidate_eligible(item, entity.original)]
        max_rank = max([int(item.get("specificity_rank", 0)) for item in eligible] or [0])
        entity.candidates = [self._candidate_from_raw(entity, item, profile, pseudonym, max_rank=max_rank) for item in eligible]
        terminal_meta = {"candidate_id": f"PSEUDONYM_{entity.entity_type}_{entity.entity_id}", "level_code": "TYPED_PSEUDONYM", "method": "case_scoped_vault", "preserves_facts": ()}
        terminal_preserves = _preserves(entity, pseudonym, terminal_meta, profile, True)
        terminal_utility = entity.metadata.get("pseudonym_utility_loss")
        if terminal_utility is None:
            terminal_utility = 0.0 if terminal_preserves else float(sum(1 for _ in profile.mandatory_facts))
        entity.candidates.append(Candidate(entity.entity_id, entity.entity_type, pseudonym, "PSEUDONYMIZE", float(terminal_utility), 0.0, "TYPED_PSEUDONYM", "Finaira MappingVault", terminal_meta, terminal_preserves, True, False))

    def _candidate_from_raw(self, entity: EntitySpec, raw: Mapping[str, Any], profile: TaskProfile, pseudonym: str, *, max_rank: int = 0) -> Candidate:
        meta = dict(raw.get("metadata") or {})
        for key in ("candidate_id", "level_code", "specificity_rank", "canonical_id", "country_code", "preserves_facts", "utility_loss", "specificity"):
            if key in raw and key not in meta:
                meta[key] = raw[key]
        text = str(raw.get("text") or raw.get("representation") or "")
        specificity, scoring_method, scoring_meta = _specificity_for({**raw, "metadata": meta}, max_rank)
        meta.update(scoring_meta)
        meta["level_code"] = raw.get("level_code", meta.get("level_code"))
        terminal = bool(raw.get("terminal_pseudonym") or meta.get("terminal_pseudonym") or raw.get("transformation") == "PSEUDONYMIZE")
        preserves = _preserves(entity, text, meta, profile, terminal)
        utility = raw.get("utility_loss", meta.get("utility_loss"))
        overrides = entity.metadata.get("utility_by_level") or {}
        level_code = raw.get("level_code", meta.get("level_code"))
        if level_code in overrides:
            utility = overrides[level_code]
        if utility is None:
            utility = 0.0 if preserves else float(sum(1 for _ in profile.mandatory_facts))
        return Candidate(entity.entity_id, entity.entity_type, text, "PSEUDONYMIZE" if terminal else "GENERALIZE", float(utility), specificity, raw.get("level_code"), raw.get("source"), {**meta, "candidate_id": raw.get("candidate_id", meta.get("candidate_id")), "lookup_source": entity.lookup.get("mode", "supplied")}, preserves, terminal, False)

    @staticmethod
    def _valid_candidates(entity: EntitySpec) -> list[Candidate]:
        return [c for c in entity.candidates if c.text and not c.forbidden_original and not c.terminal_pseudonym or c.terminal_pseudonym]

    @staticmethod
    def _allowed(entity: EntitySpec) -> list[Candidate]:
        return [c for c in V2Optimizer._valid_candidates(entity) if c.preserves_mandatory and c.specificity is not None]

    def _metrics(self, selections: list[tuple[EntitySpec, Candidate]], elapsed_ms: float, *, status: str, solver_status: int | None = None, method: str) -> dict[str, Any]:
        specificity = sum(float(candidate.specificity or 0.0) for _, candidate in selections)
        utility = sum(float(candidate.utility_loss or 0.0) for _, candidate in selections)
        detailed = sum(1 for _, candidate in selections if float(candidate.specificity or 0.0) >= 0.8)
        return {
            "total_utility_loss": round(utility, 6),
            "total_specificity": round(specificity, 6),
            "normalized_specificity": round(specificity / len(selections), 6) if selections else 0.0,
            "detailed_qi_count": detailed,
            "generalized_entity_count": sum(1 for _, c in selections if c.transformation == "GENERALIZE"),
            "pseudonymized_entity_count": sum(1 for _, c in selections if c.terminal_pseudonym),
            "mandatory_fact_satisfaction": all(c.preserves_mandatory for _, c in selections),
            "policy_compliance": status == "FEASIBLE",
            "runtime_ms": round(elapsed_ms, 3),
            "solver_status": solver_status,
            "method": method,
        }

    def _result(self, request: OptimizationRequest, profile: TaskProfile, selections: list[tuple[EntitySpec, Candidate]], *, max_utility_loss: float, method: str, status: str, elapsed_ms: float, solver_status: int | None = None, reason: str | None = None, threshold: float = 0.8, detailed_limit: int | None = None) -> dict[str, Any]:
        transformed = request.document
        if status == "FEASIBLE":
            spans = []
            for entity, candidate in selections:
                if entity.start is None or entity.end is None:
                    raise ValueError(f"MISSING_SPAN:{entity.entity_id}")
                if request.document[entity.start:entity.end] != entity.original:
                    raise ValueError(f"SPAN_VALUE_MISMATCH:{entity.entity_id}")
                spans.append((entity.start, entity.end, candidate.text))
            for start, end, replacement in sorted(spans, reverse=True):
                transformed = transformed[:start] + replacement + transformed[end:]
        metrics = self._metrics(selections, elapsed_ms, status=status, solver_status=solver_status, method=method)
        metrics.update({"max_utility_loss": max_utility_loss, "detailed_qi_threshold": threshold, "detailed_qi_limit": detailed_limit})
        return {
            "status": status,
            "method": method,
            "case_id": request.case_id,
            "task_id": profile.task_id,
            "transformed_document": transformed if status == "FEASIBLE" else None,
            "selected_candidates": [{"entity_id": e.entity_id, "entity_type": e.entity_type, "text": c.text, "candidate": c.to_dict()} for e, c in selections],
            "metrics": metrics,
            "reason": reason,
        }

    def independent_baseline(self, request: OptimizationRequest | Mapping[str, Any], *, max_utility_loss: float = math.inf) -> dict[str, Any]:
        started = time.perf_counter()
        request, profile, _ = self.prepare(request)
        selections = []
        for entity in request.entities:
            allowed = self._allowed(entity)
            if not allowed:
                return self._result(request, profile, [], max_utility_loss=max_utility_loss, method="INDEPENDENT_BASELINE", status="INFEASIBLE", elapsed_ms=(time.perf_counter() - started) * 1000, reason=f"NO_ALLOWED_CANDIDATE:{entity.entity_id}")
            chosen = min(allowed, key=lambda c: (c.utility_loss if c.utility_loss is not None else math.inf, c.specificity if c.specificity is not None else math.inf, c.metadata.get("candidate_id") or ""))
            selections.append((entity, chosen))
        total = sum(float(c.utility_loss or 0.0) for _, c in selections)
        status = "FEASIBLE" if total <= max_utility_loss else "BUDGET_EXCEEDED"
        return self._result(request, profile, selections, max_utility_loss=max_utility_loss, method="INDEPENDENT_BASELINE", status=status, elapsed_ms=(time.perf_counter() - started) * 1000, reason=None if status == "FEASIBLE" else "BASELINE_EXCEEDS_UTILITY_BUDGET")

    def greedy_baseline(self, request: OptimizationRequest | Mapping[str, Any], *, max_utility_loss: float, detailed_qi_threshold: float = 0.8, detailed_qi_limit: int | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        request, profile, _ = self.prepare(request)
        selections: list[tuple[EntitySpec, Candidate]] = []
        for entity in request.entities:
            allowed = self._allowed(entity)
            if not allowed:
                return self._result(request, profile, [], max_utility_loss=max_utility_loss, method="GREEDY", status="INFEASIBLE", elapsed_ms=(time.perf_counter() - started) * 1000, reason=f"NO_ALLOWED_CANDIDATE:{entity.entity_id}")
            selections.append((entity, min(allowed, key=lambda c: (c.utility_loss or 0.0, c.specificity or 0.0, c.metadata.get("candidate_id") or ""))))
        def valid(current):
            return sum(c.utility_loss or 0.0 for _, c in current) <= max_utility_loss and (detailed_qi_limit is None or sum(1 for _, c in current if (c.specificity or 0.0) >= detailed_qi_threshold) <= detailed_qi_limit)
        while True:
            best = None
            for index, (entity, current) in enumerate(selections):
                for candidate in self._allowed(entity):
                    if candidate.metadata.get("candidate_id") == current.metadata.get("candidate_id"):
                        continue
                    proposal = list(selections); proposal[index] = (entity, candidate)
                    delta_s = (current.specificity or 0.0) - (candidate.specificity or 0.0)
                    delta_u = (candidate.utility_loss or 0.0) - (current.utility_loss or 0.0)
                    if delta_s <= 0 or not valid(proposal):
                        continue
                    ratio = math.inf if delta_u <= 0 else delta_s / delta_u
                    key = (ratio, delta_s, -delta_u, str(candidate.metadata.get("candidate_id") or ""))
                    if best is None or key > best[0]:
                        best = (key, proposal)
            if best is None:
                break
            selections = best[1]
        status = "FEASIBLE" if valid(selections) else "INFEASIBLE"
        return self._result(request, profile, selections, max_utility_loss=max_utility_loss, method="GREEDY", status=status, elapsed_ms=(time.perf_counter() - started) * 1000, reason=None if status == "FEASIBLE" else "GREEDY_CONSTRAINTS_UNSATISFIED", threshold=detailed_qi_threshold, detailed_limit=detailed_qi_limit)

    def v2_milp(self, request: OptimizationRequest | Mapping[str, Any], *, max_utility_loss: float, detailed_qi_threshold: float = 0.8, detailed_qi_limit: int | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        request, profile, _ = self.prepare(request)
        choices = []
        for entity in request.entities:
            allowed = self._allowed(entity)
            if not allowed:
                return self._result(request, profile, [], max_utility_loss=max_utility_loss, method="V2_MILP", status="INFEASIBLE", elapsed_ms=(time.perf_counter() - started) * 1000, solver_status=2, reason=f"NO_ALLOWED_CANDIDATE:{entity.entity_id}")
            choices.append(allowed)
        flat = [(i, c) for i, group in enumerate(choices) for c in group]
        n = len(flat)
        objective = np.array([float(c.specificity) + (index * 1e-9) for index, (_, c) in enumerate(flat)], dtype=float)
        integrality = np.ones(n)
        bounds = Bounds(np.zeros(n), np.ones(n))
        rows, lower, upper = [], [], []
        for entity_index, group in enumerate(choices):
            rows.append([1.0 if item_index == entity_index else 0.0 for item_index, _ in flat]); lower.append(1.0); upper.append(1.0)
        rows.append([float(c.utility_loss or 0.0) for _, c in flat]); lower.append(-np.inf); upper.append(float(max_utility_loss))
        if detailed_qi_limit is not None:
            rows.append([1.0 if (c.specificity or 0.0) >= detailed_qi_threshold else 0.0 for _, c in flat]); lower.append(-np.inf); upper.append(float(detailed_qi_limit))
        constraints = [LinearConstraint(np.asarray(rows, dtype=float), np.asarray(lower), np.asarray(upper))]
        first = milp(objective, integrality=integrality, bounds=bounds, constraints=constraints, options={"presolve": True})
        if not first.success:
            return self._result(request, profile, [], max_utility_loss=max_utility_loss, method="V2_MILP", status="INFEASIBLE", elapsed_ms=(time.perf_counter() - started) * 1000, solver_status=int(first.status), reason=str(first.message), threshold=detailed_qi_threshold, detailed_limit=detailed_qi_limit)
        z_star = float(np.dot(np.array([float(c.specificity) for _, c in flat]), first.x))
        rows2 = list(rows) + [[float(c.specificity) for _, c in flat]]
        lower2 = list(lower) + [-np.inf]
        upper2 = list(upper) + [z_star + 1e-7]
        secondary = np.array([float(c.utility_loss or 0.0) + index * 1e-9 for index, (_, c) in enumerate(flat)], dtype=float)
        second = milp(secondary, integrality=integrality, bounds=bounds, constraints=[LinearConstraint(np.asarray(rows2), np.asarray(lower2), np.asarray(upper2))], options={"presolve": True})
        chosen_vector = second.x if second.success else first.x
        selections = []
        for entity_index, group in enumerate(choices):
            group_indices = [index for index, (i, _) in enumerate(flat) if i == entity_index]
            chosen_index = max(group_indices, key=lambda index: float(chosen_vector[index]))
            selections.append((request.entities[entity_index], flat[chosen_index][1]))
        result = self._result(request, profile, selections, max_utility_loss=max_utility_loss, method="V2_MILP", status="FEASIBLE", elapsed_ms=(time.perf_counter() - started) * 1000, solver_status=int(second.status if second.success else first.status), threshold=detailed_qi_threshold, detailed_limit=detailed_qi_limit)
        result["optimization"] = {"b_star": result["metrics"]["total_specificity"], "first_stage_specificity": z_star, "lexicographic_secondary_stage": bool(second.success), "variables": n, "constraints": len(rows2), "message": str(second.message if second.success else first.message)}
        result["decision_trace"] = [self._explain(entity, candidate, profile, result["metrics"]) for entity, candidate in selections]
        return result

    @staticmethod
    def _explain(entity: EntitySpec, candidate: Candidate, profile: TaskProfile, metrics: Mapping[str, Any]) -> dict[str, Any]:
        return {"entity_id": entity.entity_id, "entity_type": entity.entity_type, "selected_candidate": candidate.text, "transformation": candidate.transformation, "specificity": candidate.specificity, "utility_loss": candidate.utility_loss, "scoring_method": candidate.metadata.get("method"), "reason": "Selected by document-level specificity minimization subject to mandatory facts, policy and configured utility/QI constraints.", "mandatory_facts": list(profile.mandatory_facts), "terminal_pseudonym": candidate.terminal_pseudonym}

    def compare(self, request: OptimizationRequest | Mapping[str, Any], *, max_utility_loss: float, detailed_qi_threshold: float = 0.8, detailed_qi_limit: int | None = None, evaluator: Callable[[str, TaskProfile], bool] | None = None, targets: EvaluationTargets | None = None) -> dict[str, Any]:
        request_obj = request if isinstance(request, OptimizationRequest) else OptimizationRequest.from_dict(request)
        baseline = self.independent_baseline(request_obj, max_utility_loss=max_utility_loss)
        greedy = self.greedy_baseline(request_obj, max_utility_loss=max_utility_loss, detailed_qi_threshold=detailed_qi_threshold, detailed_qi_limit=detailed_qi_limit)
        v2 = self.v2_milp(request_obj, max_utility_loss=max_utility_loss, detailed_qi_threshold=detailed_qi_threshold, detailed_qi_limit=detailed_qi_limit)
        profile = resolve_task_profile(request_obj.task, request_obj.explicit_requirements)
        out = {"request": {"case_id": request_obj.case_id, "task": request_obj.task, "entity_ids": [e.entity_id for e in request_obj.entities]}, "baseline": baseline, "greedy": greedy, "v2": v2, "evaluation_targets": (targets or EvaluationTargets()).to_dict(), "evaluation": {"status": "OPTIMIZATION_COMPARISON_ONLY", "task_performance_validated": False}}
        if evaluator and profile:
            for name, result in (("baseline", baseline), ("greedy", greedy), ("v2", v2)):
                result["metrics"]["task_success"] = bool(result.get("transformed_document") and evaluator(result["transformed_document"], profile))
            out["evaluation"] = {"status": "DETERMINISTIC_EVALUATOR", "task_performance_validated": True, "baseline_task_success": baseline["metrics"].get("task_success"), "v2_task_success": v2["metrics"].get("task_success")}
        s1, s2 = baseline["metrics"].get("total_specificity"), v2["metrics"].get("total_specificity")
        reduction = None if not s1 else round((s1 - s2) / s1 * 100, 4)
        out["evaluation"]["structural_disclosure_reduction_pct"] = reduction
        out["evaluation"]["label"] = "Structural Disclosure Reduction; not re-identification risk reduction"
        target = targets or EvaluationTargets()
        out["evaluation"]["criteria"] = {
            "specificity_reduction_target": reduction is not None and reduction >= target.min_specificity_reduction_pct,
            "mandatory_fact_preservation": v2["metrics"].get("mandatory_fact_satisfaction") if target.require_mandatory_fact_preservation else True,
            "policy_compliance": v2["metrics"].get("policy_compliance") if target.require_policy_compliance else True,
            "latency_budget": target.latency_budget_ms is None or v2["metrics"].get("runtime_ms", math.inf) <= target.latency_budget_ms,
            "task_accuracy_target": None,
        }
        if out["evaluation"]["task_performance_validated"]:
            baseline_success = bool(out["evaluation"].get("baseline_task_success"))
            v2_success = bool(out["evaluation"].get("v2_task_success"))
            out["evaluation"]["criteria"]["task_accuracy_target"] = v2_success or not baseline_success
        out["evaluation"]["validated_success"] = bool(out["evaluation"]["task_performance_validated"] and all(value is True for value in out["evaluation"]["criteria"].values()))
        return out

    def sweep(self, request: OptimizationRequest | Mapping[str, Any], budgets: Iterable[float], *, detailed_qi_threshold: float = 0.8, detailed_qi_limit: int | None = None) -> list[dict[str, Any]]:
        points = []
        for budget in budgets:
            result = self.v2_milp(request, max_utility_loss=float(budget), detailed_qi_threshold=detailed_qi_threshold, detailed_qi_limit=detailed_qi_limit)
            points.append({"max_utility_loss": float(budget), "status": result["status"], "specificity": result["metrics"].get("total_specificity"), "utility_loss": result["metrics"].get("total_utility_loss"), "runtime_ms": result["metrics"].get("runtime_ms"), "selected_candidates": result.get("selected_candidates", []), "solver_status": result["metrics"].get("solver_status")})
        return points


def _span(document: str, text: str, occurrence: int = 1) -> tuple[int, int]:
    start = -1
    for _ in range(occurrence):
        start = document.find(text, start + 1)
        if start < 0:
            raise ValueError(f"EXAMPLE_SPAN_NOT_FOUND:{text}")
    return start, start + len(text)


def build_real_examples(db_path: str | Path = "data/processed/finaira_generalization.db") -> dict[str, dict[str, Any]]:
    """Create only policy-generalizable examples with exact DB coverage.

    The function checks each example with ``GeneralizationDB`` before returning
    it. A missing or review-only direct match raises rather than inventing a
    candidate. This is the source for the V2 playground samples.
    """
    db = GeneralizationDB(db_path)
    document = "Customer __FN_PERSON_0001__, aged 28, works as a Software Engineer at National Bank of Egypt and is Egyptian."
    specs = [("age-1", "AGE", "28"), ("job-1", "JOB_TITLE", "Software Engineer"), ("bank-1", "BANK", "National Bank of Egypt"), ("nat-1", "NATIONALITY", "Egyptian")]
    entities = []
    for entity_id, entity_type, original in specs:
        result = db.get_candidates(entity_type, original, output_language="en", include_review_candidates=False, input_language="en")
        if result.get("resolution_status") not in PRODUCTION_STATUSES or not any(c.get("is_exact") and not c.get("is_suppression") for c in result.get("candidates", [])):
            raise RuntimeError(f"REAL_EXAMPLE_REQUIRES_EXACT_DIRECT_MATCH:{entity_type}:{original}:{result.get('resolution_status')}")
        start, end = _span(document, original)
        entities.append({"id": entity_id, "type": entity_type, "original": original, "start": start, "end": end, "identity_key": result.get("canonical_id")})
    arabic_document = "العميل __FN_PERSON_0001__، عمره ٢٨ سنة، يعمل كمهندس برمجيات في البنك الأهلي المصري وهو مصري."
    arabic_specs = [("age-ar-1", "AGE", "٢٨"), ("job-ar-1", "JOB_TITLE", "مهندس برمجيات"), ("bank-ar-1", "BANK", "البنك الأهلي المصري"), ("nat-ar-1", "NATIONALITY", "مصري")]
    arabic_entities = []
    for entity_id, entity_type, original in arabic_specs:
        result = db.get_candidates(entity_type, original, output_language="ar", include_review_candidates=False, input_language="ar")
        if result.get("resolution_status") not in PRODUCTION_STATUSES or not any(c.get("is_exact") and not c.get("is_suppression") for c in result.get("candidates", [])):
            raise RuntimeError(f"REAL_ARABIC_EXAMPLE_REQUIRES_EXACT_DIRECT_MATCH:{entity_type}:{original}:{result.get('resolution_status')}")
        start, end = _span(arabic_document, original)
        arabic_entities.append({"id": entity_id, "type": entity_type, "original": original, "start": start, "end": end, "language": "ar", "identity_key": result.get("canonical_id")})
    return {
        "real_professional_and_demographic": {"case_id": "example-real-001", "task": "professional_summary", "document": document, "entities": entities},
        "real_arabic_exact_direct": {"case_id": "example-real-ar-001", "task": "customer_demographic_summary", "document": arabic_document, "entities": arabic_entities},
    }


def exhaustive_optimum(optimizer: V2Optimizer, request: OptimizationRequest | Mapping[str, Any], *, max_utility_loss: float, detailed_qi_threshold: float = 0.8, detailed_qi_limit: int | None = None) -> dict[str, Any]:
    """Exact enumeration for small fixtures only; never use for production."""
    request, profile, _ = optimizer.prepare(request)
    groups = [optimizer._allowed(entity) for entity in request.entities]
    best = None
    for combination in itertools.product(*groups):
        utility = sum(candidate.utility_loss or 0.0 for candidate in combination)
        detailed = sum(1 for candidate in combination if (candidate.specificity or 0.0) >= detailed_qi_threshold)
        if utility > max_utility_loss or detailed_qi_limit is not None and detailed > detailed_qi_limit:
            continue
        specificity = sum(candidate.specificity or 0.0 for candidate in combination)
        key = (specificity, utility, tuple(str(candidate.metadata.get("candidate_id") or "") for candidate in combination))
        if best is None or key < best[0]:
            best = (key, combination)
    if best is None:
        return {"status": "INFEASIBLE", "specificity": None, "utility_loss": None, "selected_candidates": []}
    return {"status": "FEASIBLE", "specificity": best[0][0], "utility_loss": best[0][1], "selected_candidates": [candidate.to_dict() for candidate in best[1]], "task_id": profile.task_id}


def make_golden_fixture() -> dict[str, Any]:
    """Return the required fixed synthetic optimizer fixture.

    ``LOCATION`` is intentionally not a production policy type in Finaira's
    current table. It is retained only because the V2 specification requires
    this exact isolated optimizer test; it is never emitted by
    ``build_real_examples`` or accepted as a production database example.
    """
    document = "Customer __FN_PERSON_0001__, aged 28, works as a Software Engineer in Zamalek."
    age_start, age_end = _span(document, "28")
    job_start, job_end = _span(document, "Software Engineer")
    loc_start, loc_end = _span(document, "Zamalek")
    return {
        "case_id": "golden-synthetic-001", "task": "professional_summary", "synthetic_fixture": True,
        "document": document,
        "entities": [
            {"id": "age", "type": "AGE", "original": "28", "start": age_start, "end": age_end, "metadata": {"synthetic_candidates": [{"candidate_id": "age-band", "text": "25–34", "level_code": "WIDE_BAND", "utility_loss": 0, "specificity": 0.50}, {"candidate_id": "age-pseudo", "text": "__FN_AGE_0001__", "level_code": "TYPED_PSEUDONYM", "utility_loss": 0, "specificity": 0, "terminal_pseudonym": True}] }},
            {"id": "job", "type": "JOB_TITLE", "original": "Software Engineer", "start": job_start, "end": job_end, "metadata": {"synthetic_candidates": [{"candidate_id": "job-it", "text": "IT Professional", "level_code": "ISCO_MAJOR", "utility_loss": 0, "specificity": 0.80}, {"candidate_id": "job-tech", "text": "Technology Worker", "level_code": "ISCO_SUB_MAJOR", "utility_loss": 2, "specificity": 0.40}, {"candidate_id": "job-pseudo", "text": "__FN_JOB_TITLE_0001__", "level_code": "TYPED_PSEUDONYM", "utility_loss": 5, "specificity": 0, "terminal_pseudonym": True}] }},
            {"id": "location", "type": "LOCATION", "original": "Zamalek", "start": loc_start, "end": loc_end, "source_entity_type": "LOCATION", "metadata": {"synthetic_candidates": [{"candidate_id": "loc-cairo", "text": "Cairo", "level_code": "CITY", "utility_loss": 0, "specificity": 0.60}, {"candidate_id": "loc-egypt", "text": "Egypt", "level_code": "COUNTRY", "utility_loss": 1, "specificity": 0.20}, {"candidate_id": "loc-pseudo", "text": "__FN_LOCATION_0001__", "level_code": "TYPED_PSEUDONYM", "utility_loss": 2, "specificity": 0, "terminal_pseudonym": True}] }},
        ],
        "requirements": {"mandatory_facts": ["meaningful_professional_category"], "precision_requirements": {}},
    }


def export_csv(comparison: Mapping[str, Any], path: str | Path) -> str:
    rows = []
    for method in ("baseline", "greedy", "v2"):
        result = comparison.get(method) or {}
        for selected in result.get("selected_candidates", []):
            candidate = selected.get("candidate", {})
            rows.append({"method": method, "entity_id": selected.get("entity_id"), "entity_type": selected.get("entity_type"), "candidate": selected.get("text"), "utility_loss": candidate.get("utility_loss"), "specificity": candidate.get("specificity"), "transformation": candidate.get("transformation"), "terminal_pseudonym": candidate.get("terminal_pseudonym"), "scoring_method": (candidate.get("metadata") or {}).get("method")})
    fieldnames = ["method", "entity_id", "entity_type", "candidate", "utility_loss", "specificity", "transformation", "terminal_pseudonym", "scoring_method"]
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames); writer.writeheader(); writer.writerows(rows)
    return str(path)


__all__ = ["Candidate", "EntitySpec", "EvaluationTargets", "OptimizationRequest", "TaskProfile", "V2Optimizer", "CaseScopedPseudonymizer", "build_real_examples", "make_golden_fixture", "exhaustive_optimum", "export_csv"]
