"""Evaluate a local/reproduced Qwen checkpoint using the official prompt and scorer."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "QuasiLeak-Bench"
sys.path.insert(0, str(VENDOR))
from prompts.render import render  # noqa: E402
from scorer.score import score  # noqa: E402


def extract_prediction(text: str) -> tuple[dict | None, str | None]:
    """Extract only a JSON object; never ask a second model to repair output."""
    text = text.strip()
    starts = [m.start() for m in re.finditer(r"\{", text)]
    decoder = json.JSONDecoder()
    for start in starts:
        try:
            obj, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("evidence", obj.get("predictions")), list):
            if "evidence" not in obj:
                obj["evidence"] = obj.pop("predictions")
            return obj, None
    return None, "NO_VALID_EVIDENCE_JSON"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--split", choices=("validation", "test"), required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter")
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--max-new-tokens", type=int, default=2048)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = args.output_dir / "raw_responses.jsonl"
    pred_path = args.output_dir / "predictions.jsonl"
    latency_path = args.output_dir / "per_request_latency.csv"

    import torch
    if not torch.cuda.is_available():
        status = {"status": "PENDING_GPU", "reason": "Qwen evaluation is intentionally not run on this CPU-only machine."}
        (args.output_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status, indent=2))
        return 2
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True)
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    rows = [json.loads(x) for x in args.dataset.open(encoding="utf-8") if x.strip()]
    # Keep the official released split membership lookup in one place.
    manifest = json.loads((VENDOR / "data/splits/split_manifest.json").read_text(encoding="utf-8"))
    wanted = set(manifest["membership"][args.split]); rows = [r for r in rows if r["sample_id"] in wanted]
    if args.limit: rows = rows[: args.limit]
    done = set()
    if args.resume and raw_path.exists():
        done = {json.loads(x)["sample_id"] for x in raw_path.open(encoding="utf-8") if x.strip()}
    latency_exists = latency_path.exists() and args.resume
    with raw_path.open("a" if args.resume else "w", encoding="utf-8", newline="\n") as raw, latency_path.open("a" if latency_exists else "w", encoding="utf-8", newline="") as lat:
        fields = ["sample_id", "input_tokens", "output_tokens", "tokenization_ms", "inference_ms", "parsing_ms", "end_to_end_ms", "ttft_ms", "tokens_per_second", "success", "error_type", "device", "precision"]
        writer = csv.DictWriter(lat, fieldnames=fields)
        if not latency_exists: writer.writeheader()
        for row in rows:
            if row["sample_id"] in done: continue
            started = time.perf_counter_ns(); token_start = time.perf_counter_ns()
            messages = render(row, shots=0)
            try:
                prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            except TypeError:
                prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tok(prompt, return_tensors="pt")
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
            token_ms = (time.perf_counter_ns() - token_start) / 1_000_000
            if torch.cuda.is_available(): torch.cuda.synchronize()
            infer_start = time.perf_counter_ns(); error = None; response = ""; generated = 0
            try:
                output = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False, use_cache=True)
                generated = int(output.shape[-1] - inputs["input_ids"].shape[-1])
                response = tok.decode(output[0, inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            if torch.cuda.is_available(): torch.cuda.synchronize()
            infer_ms = (time.perf_counter_ns() - infer_start) / 1_000_000
            parse_start = time.perf_counter_ns(); parsed, parse_error = extract_prediction(response) if not error else (None, error)
            parsing_ms = (time.perf_counter_ns() - parse_start) / 1_000_000
            if parse_error and not error: error = parse_error
            prediction = {"sample_id": row["sample_id"], "evidence": (parsed or {}).get("evidence", [])}
            e2e = (time.perf_counter_ns() - started) / 1_000_000
            raw.write(json.dumps({"sample_id": row["sample_id"], "raw_response": response, "parsed": parsed, "prediction": prediction, "success": not bool(error), "error": error}, ensure_ascii=False) + "\n"); raw.flush(); os.fsync(raw.fileno())
            writer.writerow({"sample_id": row["sample_id"], "input_tokens": int(inputs["input_ids"].shape[-1]), "output_tokens": generated, "tokenization_ms": round(token_ms, 4), "inference_ms": round(infer_ms, 4), "parsing_ms": round(parsing_ms, 4), "end_to_end_ms": round(e2e, 4), "ttft_ms": None, "tokens_per_second": round(generated / (infer_ms / 1000), 4) if infer_ms else None, "success": not bool(error), "error_type": error or "", "device": str(model.device), "precision": "bfloat16"}); lat.flush(); os.fsync(lat.fileno())
    with raw_path.open(encoding="utf-8") as fh, pred_path.open("w", encoding="utf-8", newline="\n") as out:
        for line in fh: out.write(json.dumps(json.loads(line)["prediction"], ensure_ascii=False) + "\n")
    metrics = score(pred_path, args.dataset, split=args.split)
    (args.output_dir / "official_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    status = {"status": "COMPLETE", "model": args.model, "adapter": args.adapter, "split": args.split, "rows": len(rows), "max_new_tokens": args.max_new_tokens}
    (args.output_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
