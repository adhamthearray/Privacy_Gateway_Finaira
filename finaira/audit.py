"""Small JSON-lines audit log for local POC testing."""
import json
from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    def __init__(self, path: str | Path = "logs/pipeline.log", include_output: bool = True):
        self.path = Path(path)
        self.include_output = include_output

    def record(self, result) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": result.status,
            "error_code": result.error_code,
        }
        if self.include_output:
            entry["output"] = result.output
        with self.path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
