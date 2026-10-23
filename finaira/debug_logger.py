"""Verbose local debugging logger for development/testing only."""
import json
from datetime import datetime, timezone
from pathlib import Path


class DebugLogger:
    def __init__(self, path: str | Path = "logs/debug.log", print_console: bool = True):
        self.path = Path(path)
        self.print_console = print_console

    def event(self, name: str, **data) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": name,
            **data,
        }
        line = json.dumps(entry, ensure_ascii=False, default=str)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
        if self.print_console:
            print(f"[POC4] {name}: {json.dumps(data, ensure_ascii=False, default=str)}")

    def record(self, result) -> None:
        self.event("result", status=result.status, error_code=result.error_code, output=result.output)

    def pipeline_summary(self, *, original_document, sanitized_document,
                         sanitized_response, reversed_response, status, error_code=None):
        self.event(
            "pipeline_summary",
            status=status,
            error_code=error_code,
            original_document=original_document,
            sanitized_document=sanitized_document,
            sanitized_response=sanitized_response,
            reversed_response=reversed_response,
        )
