from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass
class DetectorResponse:
    decision: str
    protected_attribute: str | None = None
    evidence_spans: list[dict[str, Any]] = field(default_factory=list)
    raw_response: str | None = None
    latency_seconds: float = 0.0
    error: str | None = None

    def as_dict(self):
        return self.__dict__.copy()


class SyntheticRuleDetector:
    """Explicitly synthetic detector for local tests; never a real result."""

    def predict(self, case: Mapping[str, Any], rendered: Mapping[str, Any]) -> DetectorResponse:
        started = time.perf_counter()
        selected = case.get("_selection", {})
        for group in case.get("gold", {}).get("verified_groups", []):
            if all(int(selected.get(entity_id, 0)) < int(group.get("break_level", 1)) for entity_id in group["entity_ids"]):
                spans = []
                for entity_id in group["entity_ids"]:
                    span = rendered["entity_spans"].get(entity_id)
                    if span:
                        spans.append({"entity_id": entity_id, **span})
                return DetectorResponse("RISK", group["attribute"], spans, "synthetic_rule", time.perf_counter() - started)
        return DetectorResponse("NO_RISK", raw_response="synthetic_rule", latency_seconds=time.perf_counter() - started)


def parse_qlb_response(raw: str) -> tuple[str, str | None, list[dict[str, Any]], str | None]:
    text = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.DOTALL).strip()
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        evidence = obj.get("evidence") if isinstance(obj, dict) else None
        if not isinstance(evidence, list):
            continue
        spans = []
        attr = None
        for group in evidence:
            if not isinstance(group, dict) or not isinstance(group.get("attribute"), str) or not isinstance(group.get("spans"), list):
                return "UNCERTAIN", None, [], "INVALID_EVIDENCE_SCHEMA"
            attr = attr or group["attribute"]
            for span_text in group["spans"]:
                if isinstance(span_text, str):
                    spans.append({"text": span_text, "attribute": group["attribute"]})
        return ("RISK" if spans else "NO_RISK"), attr, spans, None
    return "UNCERTAIN", None, [], "NO_VALID_EVIDENCE_JSON"


class QwenQLBDetector:
    """Real QLB detector adapter. Loads only an adapter/full checkpoint."""

    def __init__(self, model, processor, render_fn, *, device="cuda", max_new_tokens=2048, thinking=False):
        self.model = model
        self.processor = processor
        self.render_fn = render_fn
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.thinking = thinking
        self.calls = 0

    @classmethod
    def from_checkpoint(cls, checkpoint_dir, *, device_map="auto", max_new_tokens=2048, thinking=False, quantization_config=None):
        import torch
        from transformers import AutoModelForMultimodalLM, AutoProcessor
        from peft import PeftModel
        from huggingface_hub import snapshot_download
        from prompts.render import render
        from pathlib import Path
        checkpoint = Path(checkpoint_dir)
        adapter_config = checkpoint / "adapter_config.json"
        if adapter_config.exists():
            config = json.loads(adapter_config.read_text(encoding="utf-8"))
            base_id = config.get("base_model_name_or_path")
            if not base_id or not (checkpoint / "adapter_model.safetensors").exists():
                raise RuntimeError("INVALID_PEFT_CHECKPOINT")
            base_path = snapshot_download(base_id, local_dir="/kaggle/working/test_v3_base") if "://" not in str(base_id) else base_id
            processor = AutoProcessor.from_pretrained(base_path)
            model_kwargs = {"dtype": torch.float16, "device_map": device_map, "low_cpu_mem_usage": True}
            if quantization_config is not None:
                model_kwargs["quantization_config"] = quantization_config
            base = AutoModelForMultimodalLM.from_pretrained(base_path, **model_kwargs)
            model = PeftModel.from_pretrained(base, str(checkpoint), is_trainable=False)
        elif (checkpoint / "config.json").exists():
            processor = AutoProcessor.from_pretrained(str(checkpoint))
            model_kwargs = {"dtype": torch.float16, "device_map": device_map, "low_cpu_mem_usage": True}
            if quantization_config is not None:
                model_kwargs["quantization_config"] = quantization_config
            model = AutoModelForMultimodalLM.from_pretrained(str(checkpoint), **model_kwargs)
        else:
            raise RuntimeError("CHECKPOINT_NOT_PEFT_OR_MERGED")
        model.eval()
        return cls(model, processor, render, device="cuda", max_new_tokens=max_new_tokens, thinking=thinking)

    def predict(self, case: Mapping[str, Any], rendered: Mapping[str, Any]) -> DetectorResponse:
        import torch
        started = time.perf_counter()
        row = dict(case)
        row["document"] = rendered["text"]
        try:
            messages = self.render_fn(row, shots=0)
            try:
                inputs = self.processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt", enable_thinking=self.thinking)
            except TypeError:
                inputs = self.processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt")
            inputs = inputs.to(self.model.device)
            input_tokens = inputs["input_ids"].shape[-1]
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            with torch.inference_mode():
                output = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens, do_sample=False, use_cache=True, pad_token_id=self.processor.tokenizer.eos_token_id)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            raw = self.processor.decode(output[0][input_tokens:], skip_special_tokens=True)
            decision, attr, spans, error = parse_qlb_response(raw)
            mapped = []
            for span in spans:
                match_id = next((item_id for item_id, item in rendered["entity_spans"].items() if item["text"] == span["text"]), None)
                mapped.append({**span, "entity_id": match_id} if match_id else span)
            self.calls += 1
            return DetectorResponse(decision, attr, mapped, raw, time.perf_counter() - started, error)
        except Exception as exc:
            self.calls += 1
            return DetectorResponse("UNCERTAIN", raw_response=None, latency_seconds=time.perf_counter() - started, error=f"{type(exc).__name__}: {exc}")
