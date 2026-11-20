from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = {}
    languages = {}
    tp = fp = fn = tn = 0
    for result in results:
        statuses[result["status"]] = statuses.get(result["status"], 0) + 1
        languages.setdefault(result["language"], {"cases": 0, "loss": 0.0})
        languages[result["language"]]["cases"] += 1
        languages[result["language"]]["loss"] += result.get("normalized_loss", 0.0)
        expected_risk = bool(result.get("gold", {}).get("verified_groups"))
        initial_response = (result.get("iterations") or [{}])[0].get("response", {})
        predicted_risk = initial_response.get("decision") == "RISK"
        if predicted_risk and expected_risk:
            tp += 1
        elif predicted_risk:
            fp += 1
        elif expected_risk:
            fn += 1
        else:
            tn += 1
    for value in languages.values():
        value["average_normalized_loss"] = value["loss"] / value["cases"] if value["cases"] else None
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {
        "cases": len(results),
        "statuses": statuses,
        "languages": languages,
        "accepted_no_risk_detected": sum(result["status"] in {"NO_RISK_DETECTED", "NO_RISK_AFTER_REPAIR"} for result in results),
        "unresolved": sum(result["status"].startswith("UNRESOLVED") for result in results),
        "average_normalized_loss": sum(result.get("normalized_loss", 0.0) for result in results) / len(results) if results else None,
        "detector_calls": sum(result.get("detector_calls", 0) for result in results),
        "detector_seconds": sum(result.get("detector_latency_seconds", 0.0) for result in results),
        "verified_gold_initial_detection": {
            "gold_risk_cases": tp + fn,
            "gold_control_cases": tn + fp,
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "true_negative": tn,
            "precision": precision,
            "recall": recall,
            "f1": (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and precision + recall else None,
            "scope": "Initial detector decision against the explicit synthetic finite-rule gold; not a real-world privacy metric.",
        },
        "note": "No-risk detection is not a guarantee of privacy or absence of real-world inference."
    }


def write_html(results: list[dict[str, Any]], summary: dict[str, Any], path: str | Path) -> None:
    cards = []
    for result in results:
        entity_rows = "".join(
            f"<tr><td>{html.escape(str(entity['id']))}</td><td>{html.escape(str(entity['entity_type']))}</td><td>{html.escape(str(entity['original']))}</td><td>{html.escape(str(entity.get('candidates')))}</td></tr>"
            for entity in result["entities"]
        )
        cards.append(f"""<article class='case' data-status='{html.escape(result['status'])}' data-language='{html.escape(result['language'])}'><h2>{html.escape(result['case_id'])} <small>{html.escape(result['language'])}</small></h2><p><b>Status:</b> {html.escape(result['status'])} &nbsp; <b>Loss:</b> {result['normalized_loss']:.4f} &nbsp; <b>Detector calls:</b> {result['detector_calls']}</p><h3>Initial document</h3><pre dir='auto'>{html.escape(result['initial_document'])}</pre><h3>Final sanitized document</h3><pre dir='auto' class='final'>{html.escape(result['final_document'])}</pre><h3>Entities and ladders</h3><table><tr><th>ID</th><th>Type</th><th>Original</th><th>Candidates</th></tr>{entity_rows}</table><h3>Iterations</h3><pre>{html.escape(json.dumps(result['iterations'], ensure_ascii=False, indent=2))}</pre><h3>Constraints and limitations</h3><pre>{html.escape(json.dumps({'cuts': result['cuts'], 'limitations': result['limitations'], 'privacy_claim': result['privacy_claim']}, ensure_ascii=False, indent=2))}</pre></article>""")
    document = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Finaira V3 report</title><style>body{{font-family:system-ui;max-width:1400px;margin:2rem auto;background:#f5f7fb;color:#172033}}header,article{{background:white;border-radius:12px;padding:1.2rem;margin:1rem 0;box-shadow:0 2px 12px #0001}}pre{{white-space:pre-wrap;border:1px solid #ddd;padding:1rem;border-radius:8px;background:#fafafa}}.final{{border:2px solid #16803c}}table{{width:100%;border-collapse:collapse}}td,th{{border:1px solid #ddd;padding:.4rem;text-align:left;vertical-align:top}}small{{color:#667085}}input,select{{padding:.6rem;margin:.3rem}}</style></head><body><header><h1>Finaira V3 — QLB-guided minimal generalization</h1><p>This is an experiment report. No-risk detection is not guaranteed privacy.</p><pre>{html.escape(json.dumps(summary, ensure_ascii=False, indent=2))}</pre><input id='search' placeholder='Search cases'><select id='status'><option value=''>All statuses</option>{''.join(f"<option>{html.escape(key)}</option>" for key in sorted(summary['statuses']))}</select></header>{''.join(cards)}<script>const s=document.getElementById('search'),f=document.getElementById('status');function go(){{document.querySelectorAll('.case').forEach(c=>c.style.display=(!s.value||c.innerText.toLowerCase().includes(s.value.toLowerCase()))&&(!f.value||c.dataset.status===f.value)?'block':'none')}}s.oninput=go;f.onchange=go;</script></body></html>"""
    Path(path).write_text(document, encoding="utf-8")
