"""Measure official Qwen3.5-4B QuasiLeak latency on CPU or one local device.

This is deliberately separate from the GPU/Qwen evaluator.  It uses the
official Qwen3.5 AutoProcessor/AutoModelForMultimodalLM interface, the
official QuasiLeak prompt renderer, and the official scorer.  CPU runs are
intended for smoke tests and latency characterization; a full 1,000-document
run may take many hours and requires substantial RAM.
"""

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


def parse_prediction(text: str) -> tuple[list, bool]:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        evidence = obj.get("evidence") if isinstance(obj, dict) else None
        if isinstance(evidence, list):
            return evidence, True
    return [], False


def _sync(torch) -> None:
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--split", choices=("validation", "test"), default="test")
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    ap.add_argument("--limit", type=int, default=1)
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    if args.limit < 1:
        ap.error("--limit must be at least 1")
    if args.max_new_tokens < 1:
        ap.error("--max-new-tokens must be at least 1")

    import torch

    if args.threads:
        torch.set_num_threads(args.threads)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda was requested, but CUDA is unavailable")
    device = torch.device(args.device)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = args.output_dir / "raw_responses.jsonl"
    pred_path = args.output_dir / "predictions.jsonl"
    latency_path = args.output_dir / "per_request_latency.csv"

    rows = [json.loads(line) for line in args.dataset.open(encoding="utf-8") if line.strip()]
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    wanted = set(manifest["membership"][args.split])
    rows = [row for row in rows if row["sample_id"] in wanted][: args.limit]

    print(f"Loading {args.model} on {device} for {len(rows)} {args.split} document(s)", flush=True)
    from transformers import AutoModelForMultimodalLM, AutoProcessor

    processor = AutoProcessor.from_pretrained(args.model)
    dtype = torch.float32 if device.type == "cpu" else torch.float16
    load_kwargs = {"torch_dtype": dtype, "low_cpu_mem_usage": True}
    if device.type == "cuda":
        load_kwargs["device_map"] = "auto"
    model = AutoModelForMultimodalLM.from_pretrained(args.model, **load_kwargs)
    if device.type == "cpu":
        model.to(device)
    model.eval()
    print(f"Model loaded; dtype={dtype}; parameters={sum(p.numel() for p in model.parameters()):,}", flush=True)

    done = set()
    if args.resume and raw_path.exists():
        done = {json.loads(line)["sample_id"] for line in raw_path.open(encoding="utf-8") if line.strip()}

    fields = ["sample_id", "input_tokens", "output_tokens", "tokenization_ms", "inference_ms", "parsing_ms", "end_to_end_ms", "tokens_per_second", "success", "error_type", "device", "precision"]
    append = args.resume and latency_path.exists()
    latencies = []
    if append:
        with latency_path.open(encoding="utf-8") as fh:
            latencies = [float(row["end_to_end_ms"]) for row in csv.DictReader(fh) if row.get("end_to_end_ms")]

    with raw_path.open("a" if args.resume else "w", encoding="utf-8") as raw, latency_path.open("a" if append else "w", encoding="utf-8", newline="") as lat:
        writer = csv.DictWriter(lat, fieldnames=fields)
        if not append:
            writer.writeheader()
        for index, row in enumerate(rows, 1):
            if row["sample_id"] in done:
                print(f"[{index}/{len(rows)}] skipped {row['sample_id']}", flush=True)
                continue
            started = time.perf_counter_ns()
            response = ""
            evidence = []
            valid = False
            error = ""
            try:
                messages = render(row, shots=0)
                token_start = time.perf_counter_ns()
                try:
                    inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt", enable_thinking=False)
                except TypeError:
                    inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt")
                inputs = inputs.to(device)
                tokenization_ms = (time.perf_counter_ns() - token_start) / 1_000_000
                input_tokens = int(inputs["input_ids"].shape[-1])
                _sync(torch)
                infer_start = time.perf_counter_ns()
                with torch.inference_mode():
                    outputs = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False, use_cache=True, pad_token_id=processor.tokenizer.eos_token_id)
                _sync(torch)
                inference_ms = (time.perf_counter_ns() - infer_start) / 1_000_000
                generated = outputs[0][input_tokens:]
                response = processor.decode(generated, skip_special_tokens=True)
                parse_start = time.perf_counter_ns()
                evidence, valid = parse_prediction(response)
                parsing_ms = (time.perf_counter_ns() - parse_start) / 1_000_000
                output_tokens = int(len(generated))
                if not valid:
                    error = "NO_VALID_EVIDENCE_JSON"
            except Exception as exc:  # preserve failed requests for audit
                error = f"{type(exc).__name__}: {exc}"
                tokenization_ms = inference_ms = parsing_ms = 0.0
                input_tokens = output_tokens = 0
            end_to_end_ms = (time.perf_counter_ns() - started) / 1_000_000
            latencies.append(end_to_end_ms)
            raw.write(json.dumps({"sample_id": row["sample_id"], "raw_response": response, "evidence": evidence, "valid": valid, "success": not bool(error), "error": error}, ensure_ascii=False) + "\n")
            writer.writerow({"sample_id": row["sample_id"], "input_tokens": input_tokens, "output_tokens": output_tokens, "tokenization_ms": round(tokenization_ms, 4), "inference_ms": round(inference_ms, 4), "parsing_ms": round(parsing_ms, 4), "end_to_end_ms": round(end_to_end_ms, 4), "tokens_per_second": round(output_tokens / (inference_ms / 1000), 4) if inference_ms else None, "success": not bool(error), "error_type": error, "device": str(device), "precision": str(dtype)})
            raw.flush(); lat.flush()
            print(f"[{index}/{len(rows)}] {'OK' if not error else 'FAILED'} | {end_to_end_ms:,.0f} ms | input={input_tokens} output={output_tokens}", flush=True)

    records = list(csv.DictReader(latency_path.open(encoding="utf-8")))
    values = [float(row["end_to_end_ms"]) for row in records]
    values.sort()
    percentile = lambda p: values[min(len(values) - 1, int((len(values) - 1) * p))] if values else None
    summary = {"model": args.model, "device": str(device), "dtype": str(dtype), "split": args.split, "documents": len(records), "successful": sum(row["success"] == "True" for row in records), "valid_json": sum(row["success"] == "True" and row.get("error_type", "") == "" for row in records), "mean_ms": sum(values) / len(values) if values else None, "median_ms": percentile(0.50), "p95_ms": percentile(0.95), "max_ms": max(values) if values else None, "max_new_tokens": args.max_new_tokens}
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
