"""Single-cell entry point for the real 50-case QLB-guided V3 run."""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

CASE_LIMIT = 50
MAX_ITERATIONS = 8
MAX_DETECTOR_CALLS_PER_CASE = 40
SOLVER_TIME_LIMIT_SECONDS = 5
USE_4BIT = True  # Request 4-bit when bitsandbytes is available; otherwise use verified fp16 fallback.
SEED = 42
DEBUG = False
MODEL_PATH = None
BASE_MODEL = "Qwen/Qwen3.5-4B"
MAX_NEW_TOKENS = 2048

# ``__file__`` exists when this is run as a .py file but not when the same
# code is pasted into a Kaggle notebook cell.
HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
WORK = Path("/kaggle/working/test_v3_results")
WORK.mkdir(parents=True, exist_ok=True)


def run(command, cwd=None):
    print(">>>", " ".join(map(str, command)), flush=True)
    subprocess.check_call([str(value) for value in command], cwd=cwd)


def find_payload_root() -> Path:
    candidates = [
        Path("/kaggle/input/test_v3"),
        Path("/kaggle/input/test-v3"),
        Path("/kaggle/input") / "test_v3",
        Path("/kaggle/input") / "test-v3",
    ]
    for candidate in candidates:
        if (candidate / "cases" / "synthetic_cases.jsonl").exists():
            return candidate
    for candidate in Path("/kaggle/input").glob("**/synthetic_cases.jsonl"):
        return candidate.parent.parent
    raise RuntimeError("test_v3 payload not found under /kaggle/input")


def find_checkpoint(root: Path) -> Path:
    if MODEL_PATH:
        selected = Path(MODEL_PATH)
        if not selected.exists():
            raise RuntimeError(f"Configured MODEL_PATH does not exist: {selected}")
        return selected
    adapters = list(root.rglob("adapter_config.json")) + list(Path("/kaggle/input").rglob("adapter_config.json"))
    adapters = sorted({item.resolve() for item in adapters})
    if len(adapters) != 1:
        raise RuntimeError(f"Expected exactly one adapter_config.json, found: {adapters}")
    return adapters[0].parent


print("Finaira V3 real QLB run", flush=True)
payload = find_payload_root()
checkpoint = find_checkpoint(payload)
print("Payload:", payload, flush=True)
print("Checkpoint:", checkpoint, flush=True)

run([
    sys.executable, "-m", "pip", "install", "-q",
    "ortools>=9.10", "PyYAML>=6.0", "transformers>=5,<6",
    "peft>=0.21.2", "accelerate>=1.0", "safetensors>=0.4",
    "huggingface_hub>=0.25", "sentencepiece>=0.2", "pillow>=10", "torchvision"
])
# Kaggle images may carry torchao 0.10, which recent PEFT rejects while
# constructing ordinary LoRA modules. It is optional for this experiment.
subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "torchao"], check=False)

sys.path.insert(0, str(payload / "src"))
sys.path.insert(0, str(payload))

import torch
from test_v3.controller import run_case
from test_v3.detector import QwenQLBDetector
from test_v3.reporting import summarize, write_html

if not torch.cuda.is_available():
    raise RuntimeError("A CUDA GPU is required for the real Kaggle run.")

adapter_config_path = checkpoint / "adapter_config.json"
if not adapter_config_path.exists() and not (checkpoint / "config.json").exists():
    raise RuntimeError("Checkpoint is neither a PEFT adapter nor a merged Hugging Face checkpoint.")
if adapter_config_path.exists():
    adapter_config = json.loads(adapter_config_path.read_text(encoding="utf-8"))
    if adapter_config.get("base_model_name_or_path") != BASE_MODEL:
        raise RuntimeError(f"Adapter base model mismatch: {adapter_config.get('base_model_name_or_path')}")
    print("Verified PEFT base model:", adapter_config["base_model_name_or_path"], flush=True)

qlb_root = Path("/kaggle/working/QuasiLeak-Bench")
qlb_ref = "75987cdf029fac5fecce160bea218b458ed46dbb"
if not (qlb_root / ".git").exists():
    run(["git", "clone", "https://github.com/Yufannnn/QuasiLeak-Bench.git", str(qlb_root)])
run(["git", "fetch", "--depth", "1", "origin", qlb_ref], cwd=qlb_root)
run(["git", "checkout", qlb_ref], cwd=qlb_root)

from test_v3 import detector as detector_module
sys.path.insert(0, str(qlb_root))

print("Loading verified fine-tuned checkpoint...", flush=True)
quantization_config = None
quantization_used = False
quantization_note = "fp16"
if USE_4BIT:
    try:
        from transformers import BitsAndBytesConfig
        import bitsandbytes  # noqa: F401
        quantization_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
        quantization_used = True
        quantization_note = "bitsandbytes_nf4_4bit"
    except Exception as exc:
        quantization_note = f"fp16_fallback: {type(exc).__name__}: {exc}"
        print("4-bit requested but unavailable; using fp16:", exc, flush=True)
detector = QwenQLBDetector.from_checkpoint(
    checkpoint,
    device_map="auto",
    max_new_tokens=MAX_NEW_TOKENS,
    thinking=False,
    quantization_config=quantization_config,
)
print("Fine-tuned checkpoint loaded; model type:", type(detector.model).__name__, "quantization:", quantization_note, flush=True)

cases_path = payload / "cases" / "synthetic_cases.jsonl"
cases = [json.loads(line) for line in cases_path.open(encoding="utf-8") if line.strip()][:CASE_LIMIT]
if len(cases) != CASE_LIMIT:
    raise RuntimeError(f"Expected {CASE_LIMIT} cases, found {len(cases)}")

print("Running genuine smoke inference on case 1...", flush=True)
smoke = run_case(cases[0], detector, max_iterations=1, max_detector_calls=1, solver_time_limit=SOLVER_TIME_LIMIT_SECONDS)
print("Smoke status:", smoke["status"], "detector calls:", smoke["detector_calls"], flush=True)

results = []
for index, case in enumerate(cases, 1):
    started = time.perf_counter()
    result = run_case(case, detector, max_iterations=MAX_ITERATIONS, max_detector_calls=MAX_DETECTOR_CALLS_PER_CASE, solver_time_limit=SOLVER_TIME_LIMIT_SECONDS)
    result["case_runtime_seconds"] = time.perf_counter() - started
    results.append(result)
    print(f"[{index}/{len(cases)}] {case['case_id']} {result['status']} loss={result['normalized_loss']:.4f} calls={result['detector_calls']}", flush=True)

with (WORK / "results.jsonl").open("w", encoding="utf-8") as handle:
    for result in results:
        handle.write(json.dumps(result, ensure_ascii=False) + "\n")

with (WORK / "detector_calls.jsonl").open("w", encoding="utf-8") as handle:
    for result in results:
        for iteration in result["iterations"]:
            handle.write(json.dumps({"case_id": result["case_id"], **iteration}, ensure_ascii=False) + "\n")
            for probe in iteration.get("subset_probes", []):
                handle.write(json.dumps({"case_id": result["case_id"], "kind": "subset_probe", **probe}, ensure_ascii=False) + "\n")

with (WORK / "failures.jsonl").open("w", encoding="utf-8") as handle:
    for result in results:
        if result["status"].startswith("UNRESOLVED"):
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")

summary = summarize(results)
summary.update({
    "real_model": True,
    "model_id": BASE_MODEL,
    "checkpoint": str(checkpoint),
    "case_limit": CASE_LIMIT,
    "max_iterations": MAX_ITERATIONS,
    "max_detector_calls_per_case": MAX_DETECTOR_CALLS_PER_CASE,
    "seed": SEED,
    "use_4bit_requested": USE_4BIT,
    "quantization_used": quantization_used,
    "quantization": quantization_note,
    "warning": "No-risk detection is not guaranteed privacy."
})
(WORK / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
write_html(results, summary, WORK / "report.html")

with (WORK / "results.csv").open("w", newline="", encoding="utf-8") as handle:
    fields = ["case_id", "language", "status", "normalized_loss", "detector_calls", "detector_latency_seconds", "solver_seconds", "fallback_applied"]
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    for result in results:
        writer.writerow({field: result.get(field) for field in fields})

(WORK / "run_config.json").write_text(json.dumps({"checkpoint": str(checkpoint), "model": BASE_MODEL, "case_limit": CASE_LIMIT, "max_iterations": MAX_ITERATIONS, "max_detector_calls_per_case": MAX_DETECTOR_CALLS_PER_CASE, "qlb_commit": qlb_ref}, indent=2), encoding="utf-8")
archive = shutil.make_archive("/kaggle/working/test_v3_results", "zip", root_dir=WORK)
print("SUMMARY", json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
print("RESULTS ZIP:", archive, flush=True)
