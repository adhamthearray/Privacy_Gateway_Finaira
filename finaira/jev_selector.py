"""English-only JEV selection for database-backed candidates."""

from __future__ import annotations

import atexit
import json
import os
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener
from urllib.parse import urlsplit

from finaira_generalization import GeneralizationDB


# AGE and DATE remain on their existing deterministic rules.
DB_ENTITY_TYPES = {
    "OCCUPATION", "JOB_TITLE", "NATIONALITY", "BANK", "CORPORATION",
    "ORGANIZATION", "UNIVERSITY", "GOVERNMENT_ENTITY",
}

# These describe the privacy context to assess; they do not prescribe a choice.
ENTITY_GUIDANCE = {
    "OCCUPATION": "Assess whether the occupation and its context could identify a person or reveal personal information.",
    "JOB_TITLE": "Assess whether the job title and its context could identify a person or reveal personal information.",
    "NATIONALITY": "Assess the sensitivity of nationality in this sentence and whether it could identify or expose a person. Do not infer residence, birthplace, ethnicity, or citizenship.",
    "BANK": "Assess whether naming the bank could reveal a person's financial relationship or activity in this sentence.",
    "CORPORATION": "Assess whether naming the company could identify a person through an employment, legal, financial, or other relationship in this sentence.",
    "ORGANIZATION": "Assess whether naming the organization could reveal a person's affiliation or activity in this sentence.",
    "UNIVERSITY": "Assess whether naming the university could reveal a person's education or affiliation in this sentence.",
    "GOVERNMENT_ENTITY": "Assess whether naming the government entity could reveal a person's involvement with a sensitive service, case, or proceeding.",
}

VALID_STATUSES = {
    "APPROVED", "CONFIGURED", "OFFICIAL", "REVIEWED",
    "SOURCE_VERIFIED", "VERIFIED",
}


class JEVSelector:
    """Get English options from SQLite and submit them to local JEV."""

    def __init__(
        self,
        db: GeneralizationDB | None = None,
        *,
        db_path: str | Path = "data/processed/finaira_generalization.db",
        base_url: str | None = None,
        jev_exe: str | Path | None = None,
        model: str = "jev-latest",
        suppression_text: str = "[REDACTED]",
    ):
        self.db = db or GeneralizationDB(db_path)
        self.base_url = (base_url or os.getenv(
            "JEV_BASE_URL", "http://127.0.0.1:8017"
        )).rstrip("/")
        parsed_url = urlsplit(self.base_url)
        if parsed_url.scheme != "http" or parsed_url.hostname not in {
            "127.0.0.1", "localhost", "::1"
        }:
            raise ValueError("JEV_MUST_USE_LOOPBACK")
        exe = jev_exe or os.getenv("JEV_EXE")
        self.jev_exe = Path(exe) if exe else None
        self.model = model
        self.suppression_text = os.getenv(
            "FINAIRA_SUPPRESSION_TEXT", suppression_text
        )
        self.process = None
        self.http = build_opener(ProxyHandler({}))

    def select_candidate(
        self, entity_type: str, value: str, sentence: str, *, context: dict | None = None
    ) -> dict:
        """Select a candidate for English input; AGE and DATE are excluded."""
        entity = entity_type.upper()
        if entity not in DB_ENTITY_TYPES:
            raise ValueError("NOT_DATABASE_BACKED_ENTITY_TYPE")

        try:
            result = self.db.get_candidates(
                entity, value, output_language="en", context=context
            )
            options = self._options(result.get("candidates", []))
        except Exception:
            return self._fallback(entity, "DATABASE_ERROR")
        if not options:
            return self._fallback(entity, "NO_ELIGIBLE_CANDIDATES", result)
        if len(options) == 1:
            return self._result(result, options[0], {}, None)

        try:
            probabilities = self._ask(entity, value, sentence, options)
            key = max(probabilities, key=probabilities.get)
            option = next(option for option in options if option["key"] == key)
            return self._result(result, option, probabilities, None)
        except Exception:
            return self._fallback(entity, "JEV_UNAVAILABLE_OR_INVALID", result)

    def close(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def _options(self, candidates: list[dict]) -> list[dict]:
        options = []
        for candidate in candidates:
            meta = candidate.get("metadata") or {}
            provenance = candidate.get("provenance") or meta.get("provenance") or {}
            suppressed = candidate.get("is_suppression", meta.get("is_suppression", False))
            if meta.get("review_only") or provenance.get("requires_policy_approval"):
                continue
            if candidate.get("is_local_only", meta.get("is_local_only")):
                continue
            if not suppressed:
                if str(candidate.get("verification_status", "")).upper() not in VALID_STATUSES:
                    continue
                if meta.get("disclosure_approved") is False:
                    continue
                if not candidate.get("available") or not candidate.get("representation"):
                    continue
            options.append({
                "key": f"option_{len(options)}",
                "candidate": candidate,
                "replacement": self.suppression_text if suppressed else candidate["representation"],
            })
        return options

    def _ask(self, entity: str, value: str, sentence: str, options: list[dict]) -> dict[str, float]:
        criteria = {
            option["key"]: (
                f"Level: {option['candidate'].get('level_code', 'GENERALIZED')}; "
                f"candidate: {option['replacement']}"
            )
            for option in options
        }
        body = {
            "model": self.model,
            "state": {"sentence": sentence, "entity": value, "entity_type": entity},
            "questions": {
                "candidate": {
                    "type": "choice",
                    "instructions": (
                        "Evaluate the candidates using the sentence, entity type, "
                        "and privacy context. Consider privacy impact and relevant "
                        "meaning. Select one listed candidate without rewriting it. "
                        + ENTITY_GUIDANCE[entity]
                    ),
                    "criteria": criteria,
                }
            },
        }
        self._ensure_server()
        request = Request(
            f"{self.base_url}/v1/systemone",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.http.open(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
        raw = data["answers"]["candidate"]["probabilities"]
        keys = {option["key"] for option in options}
        probabilities = {
            key: float(score) for key, score in raw.items()
            if key in keys and isinstance(score, (int, float))
        }
        if not probabilities:
            raise ValueError("INVALID_JEV_PROBABILITIES")
        return probabilities

    def _ensure_server(self) -> None:
        try:
            with self.http.open(f"{self.base_url}/health", timeout=1):
                return
        except (URLError, OSError, TimeoutError):
            pass
        if self.jev_exe is None or not self.jev_exe.is_file():
            raise RuntimeError("JEV_UNAVAILABLE")
        self.process = subprocess.Popen(
            [str(self.jev_exe), "serve"], cwd=str(self.jev_exe.parent),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        atexit.register(self.close)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("JEV_STARTUP_FAILED")
            try:
                with self.http.open(f"{self.base_url}/health", timeout=1):
                    return
            except (URLError, OSError, TimeoutError):
                time.sleep(0.5)
        raise RuntimeError("JEV_STARTUP_TIMEOUT")

    @staticmethod
    def _result(result: dict, option: dict, probabilities: dict, reason: str | None) -> dict:
        return {
            **result,
            "selected_candidate": option["candidate"],
            "replacement": option["replacement"],
            "probabilities": probabilities,
            "fallback_reason": reason,
        }

    def _fallback(self, entity: str, reason: str, result: dict | None = None) -> dict:
        result = result or {
            "entity_type": entity, "resolution_status": "ERROR",
            "canonical_id": None, "candidates": [],
        }
        return {
            **result,
            "selected_candidate": None,
            "replacement": self.suppression_text,
            "probabilities": {},
            "fallback_reason": reason,
        }
