"""Run a small local browser UI for experimenting with the generalization DB."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finaira_generalization.candidates import GeneralizationDB


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Finaira Generalization DB Explorer</title>
  <style>
    :root { color-scheme: dark; --bg:#111827; --panel:#1f2937; --line:#374151; --muted:#9ca3af; --good:#34d399; --warn:#fbbf24; --bad:#f87171; }
    * { box-sizing: border-box; }
    body { margin:0; background:var(--bg); color:#f3f4f6; font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif; }
    main { max-width:1250px; margin:0 auto; padding:28px 20px 56px; }
    h1 { margin:0 0 5px; font-size:28px; }
    h2 { margin:26px 0 12px; font-size:19px; }
    .sub { color:var(--muted); margin:0 0 22px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px; }
    .form { display:grid; grid-template-columns:minmax(260px,1fr) 190px 150px auto; gap:12px; align-items:end; }
    label { display:block; color:var(--muted); font-size:12px; margin-bottom:5px; }
    input, select, button { width:100%; border:1px solid #4b5563; border-radius:7px; padding:10px 11px; background:#111827; color:#f9fafb; font:inherit; }
    input:focus, select:focus { outline:2px solid #60a5fa; outline-offset:1px; }
    button { background:#2563eb; border-color:#2563eb; cursor:pointer; font-weight:600; }
    button:hover { background:#1d4ed8; }
    .options { display:flex; align-items:center; gap:8px; margin-top:13px; color:var(--muted); }
    .options input { width:auto; }
    .hint { color:var(--muted); font-size:12px; margin-top:10px; }
    .status { display:flex; flex-wrap:wrap; gap:10px; align-items:center; }
    .badge { display:inline-block; border-radius:999px; padding:4px 10px; font-weight:700; font-size:12px; background:#374151; }
    .verified { color:#052e16; background:var(--good); }
    .matched { color:#052e16; background:var(--good); }
    .review { color:#422006; background:var(--warn); }
    .ambiguous { color:#431407; background:#fb923c; }
    .notfound, .invalid { color:#450a0a; background:var(--bad); }
    .meta { color:var(--muted); font-size:13px; margin-top:10px; word-break:break-word; }
    .candidate { border:1px solid var(--line); border-radius:10px; padding:14px; margin:10px 0; background:#172033; }
    .candidate-head { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }
    .candidate-title { font-size:17px; font-weight:700; word-break:break-word; }
    .candidate-id { color:var(--muted); font:12px ui-monospace,SFMono-Regular,Consolas,monospace; word-break:break-all; margin-top:5px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:8px 18px; margin-top:12px; }
    .field { color:var(--muted); font-size:12px; }
    .field strong { color:#e5e7eb; display:block; font-size:13px; word-break:break-word; }
    details { margin-top:12px; }
    pre { white-space:pre-wrap; overflow:auto; background:#0b1020; border:1px solid var(--line); padding:10px; border-radius:7px; color:#d1d5db; font-size:12px; }
    .empty, .error { padding:15px; border-radius:8px; background:#172033; color:var(--muted); }
    .error { color:#fecaca; border:1px solid #7f1d1d; }
    @media (max-width:800px) { .form { grid-template-columns:1fr; } .candidate-head { display:block; } }
  </style>
</head>
<body>
<main>
  <h1>Finaira Generalization DB Explorer</h1>
  <p class="sub">Local, deterministic lookup. Search Arabic or English; choose the language of the returned labels.</p>

  <section class="panel">
    <form id="query-form">
      <div>
        <label for="value">Text or entity value</label>
        <input id="value" name="value" autocomplete="off" placeholder="e.g. مدير الموارد البشرية" required>
      </div>
      <div>
        <label for="type">Entity type</label>
        <select id="type" name="type">
          <option>JOB_TITLE</option><option>OCCUPATION</option><option>COUNTRY</option>
          <option>NATIONALITY</option><option>BANK</option><option>CORPORATION</option>
          <option>ORGANIZATION</option><option>UNIVERSITY</option><option>GOVERNMENT_ENTITY</option>
          <option>AGE</option><option>DATE</option>
        </select>
      </div>
      <div>
        <label for="language">Return labels in</label>
        <select id="language" name="language"><option value="en">English</option><option value="ar">العربية</option></select>
      </div>
      <button type="submit">Query database</button>
    </form>
    <div class="options">
      <input id="review" type="checkbox">
      <label for="review" style="margin:0">Include review-only candidates</label>
    </div>
    <div class="hint">The input language is detected automatically. Review-only results remain gated. This tool shows database candidates; it does not pseudonymize or select a disclosure policy.</div>
  </section>

  <section id="result" style="display:none">
    <h2>Resolution</h2>
    <div class="panel" id="summary"></div>
    <h2>Candidate chain</h2>
    <div id="candidates"></div>
  </section>
</main>
<script>
const form = document.getElementById('query-form');
const result = document.getElementById('result');
const summary = document.getElementById('summary');
const candidates = document.getElementById('candidates');
const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const json = value => esc(JSON.stringify(value ?? {}, null, 2));
const cls = status => String(status || '').toLowerCase().replace(/[^a-z]/g, '');

function field(label, value) {
  return `<div class="field">${esc(label)}<strong>${esc(value === undefined || value === null || value === '' ? '—' : value)}</strong></div>`;
}

function render(data) {
  result.style.display = 'block';
  const status = data.resolution_status || 'UNKNOWN';
  summary.innerHTML = `<div class="status"><span class="badge ${cls(status)}">${esc(status)}</span>${data.reason_code ? `<span class="badge">${esc(data.reason_code)}</span>` : ''}</div>`
    + `<div class="grid">${field('Entity type', data.entity_type)}${field('Canonical ID', data.canonical_id)}${field('Candidates', (data.candidates || []).length)}</div>`;
  const rows = data.candidates || [];
  if (!rows.length) { candidates.innerHTML = '<div class="empty">No candidates returned.</div>'; return; }
  candidates.innerHTML = rows.map((item, index) => {
    const flags = [item.is_exact && 'EXACT', item.is_local_only && 'LOCAL_ONLY', item.is_suppression && 'SUPPRESSION', item.available === false && 'UNAVAILABLE'].filter(Boolean);
    return `<article class="candidate"><div class="candidate-head"><div><div class="candidate-title">${esc(item.representation || item.label_en || item.label_ar || item.level_code || 'Unnamed candidate')}</div><div class="candidate-id">${esc(item.candidate_id)}</div></div><span class="badge">rank ${esc(item.specificity_rank ?? index)}</span></div><div class="grid">${field('Level', item.level_code)}${field('Verification', item.verification_status)}${field('Source', item.source)}${field('Taxonomy', item.taxonomy)}${field('Taxonomy code', item.taxonomy_code)}${field('Flags', flags.join(' · '))}</div><details><summary>Labels and provenance</summary><pre>${json({label_en:item.label_en,label_ar:item.label_ar,provenance:item.provenance,metadata:item.metadata})}</pre></details></article>`;
  }).join('');
  result.scrollIntoView({behavior:'smooth', block:'start'});
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const value = document.getElementById('value').value.trim();
  const type = document.getElementById('type').value;
  const language = document.getElementById('language').value;
  const review = document.getElementById('review').checked ? '1' : '0';
  summary.innerHTML = '<div class="empty">Querying the local database…</div>';
  candidates.innerHTML = '';
  result.style.display = 'block';
  try {
    const response = await fetch(`/api/query?value=${encodeURIComponent(value)}&type=${encodeURIComponent(type)}&language=${encodeURIComponent(language)}&review=${review}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Query failed');
    render(data);
  } catch (error) {
    summary.innerHTML = `<div class="error">${esc(error.message)}</div>`;
    candidates.innerHTML = '';
  }
});
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    db_path: Path

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send(HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/query":
            params = parse_qs(parsed.query)
            value = params.get("value", [""])[0].strip()
            entity_type = params.get("type", [""])[0].strip().upper()
            language = params.get("language", ["en"])[0].strip().lower()
            include_review = params.get("review", ["0"])[0] == "1"
            if not value:
                self._send(json.dumps({"error": "Enter a value to query."}).encode(), "application/json", 400)
                return
            if language not in {"ar", "en"}:
                self._send(json.dumps({"error": "Output language must be ar or en."}).encode(), "application/json", 400)
                return
            try:
                payload = GeneralizationDB(self.db_path).get_candidates(entity_type, value, language, include_review_candidates=include_review)
                self._send(json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            except Exception as exc:  # Keep the local UI usable while exposing the actual failure.
                self._send(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", 500)
            return
        self._send(b"Not found", "text/plain; charset=utf-8", 404)

    def log_message(self, format: str, *args) -> None:
        print(f"[ui] {self.address_string()} - {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "data/processed/finaira_generalization.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not args.db.exists():
        raise SystemExit(f"Database not found: {args.db}")
    Handler.db_path = args.db
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Finaira Generalization DB Explorer: http://{args.host}:{args.port}/")
    print(f"Database: {args.db}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping UI")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
