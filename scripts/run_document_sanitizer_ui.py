"""Run a local drag-and-drop UI for placeholder document policy JSON."""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finaira.document_sanitizer import prepare_document  # noqa: E402


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Finaira Document Sanitizer</title>
  <style>
    :root { color-scheme: dark; --bg:#0b1020; --panel:#121a2b; --line:#2a3854; --text:#eef3ff; --muted:#aab7d1; --accent:#8ab4ff; --good:#9be7b0; --bad:#ff9d9d; }
    * { box-sizing:border-box; }
    body { margin:0; padding:28px; background:var(--bg); color:var(--text); font:15px/1.5 system-ui,Segoe UI,sans-serif; }
    main { max-width:1100px; margin:auto; }
    h1 { margin:0 0 8px; font-size:28px; }
    p { color:var(--muted); }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px; margin:18px 0; }
    .drop { border:2px dashed var(--line); border-radius:10px; padding:20px; text-align:center; color:var(--muted); transition:.15s; }
    .drop.over { border-color:var(--accent); background:#182744; color:var(--text); }
    textarea, pre { width:100%; min-height:360px; border:1px solid var(--line); border-radius:8px; background:#09101d; color:var(--text); padding:14px; font:13px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace; }
    textarea { resize:vertical; margin-top:14px; }
    pre { white-space:pre-wrap; overflow:auto; margin:0; }
    .controls { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-top:14px; }
    button, .file { border:1px solid #5279ba; border-radius:7px; background:#1c3967; color:#fff; padding:9px 14px; cursor:pointer; font-weight:600; }
    button:hover, .file:hover { background:#28518b; }
    input[type=file] { display:none; }
    label { color:var(--muted); }
    .status { margin-top:12px; color:var(--muted); }
    .error { color:var(--bad); }
    .success { color:var(--good); }
    code { color:#c5d8ff; }
  </style>
</head>
<body>
  <main>
    <h1>Finaira Document Sanitizer</h1>
    <p>Drop a placeholder-document JSON file, or paste JSON below. The output is JSON only: pseudonymization forms for policy-pseudonymized entities and unselected database candidates for generalizable entities.</p>
    <section class="panel">
      <div id="drop" class="drop">Drop a <code>.json</code> file here</div>
      <div class="controls">
        <label class="file">Choose JSON file<input id="file" type="file" accept="application/json,.json"></label>
        <button id="sample" type="button">Load sample</button>
        <label><input id="review" type="checkbox" checked> Include review-only candidates</label>
      </div>
      <textarea id="input" spellcheck="false" placeholder='{"document_id":"doc-001","text":"[[E0001]]...","entity_map":{}}'></textarea>
      <div class="controls"><button id="run" type="button">Return policy JSON</button><span id="status" class="status"></span></div>
    </section>
    <section class="panel">
      <h2>JSON output</h2>
      <pre id="output">Waiting for a document…</pre>
    </section>
  </main>
  <script>
    const input = document.getElementById('input');
    const output = document.getElementById('output');
    const status = document.getElementById('status');
    const drop = document.getElementById('drop');
    const sample = {document_id:'doc-001', text:'[[E0001]] emailed [[E0002]]. [[E0001]] requested a refund.', entity_map:{E0001:{label:'PERSON_NAME', original_text:'Ahmed Ali', placeholder:'[[E0001]]'}, E0002:{label:'EMAIL_ADDRESS', original_text:'ahmed@example.com', placeholder:'[[E0002]]'}}};
    function show(value) { output.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2); }
    function readFile(file) { const reader = new FileReader(); reader.onload = () => { input.value = reader.result; status.textContent = `Loaded ${file.name}`; status.className = 'status success'; }; reader.readAsText(file); }
    document.getElementById('file').addEventListener('change', event => { if (event.target.files[0]) readFile(event.target.files[0]); });
    ['dragenter','dragover'].forEach(eventName => drop.addEventListener(eventName, event => { event.preventDefault(); drop.classList.add('over'); }));
    ['dragleave','drop'].forEach(eventName => drop.addEventListener(eventName, event => { event.preventDefault(); drop.classList.remove('over'); }));
    drop.addEventListener('drop', event => { const file = event.dataTransfer.files[0]; if (file) readFile(file); });
    document.getElementById('sample').addEventListener('click', () => { input.value = JSON.stringify(sample, null, 2); status.textContent = 'Sample loaded'; status.className = 'status success'; });
    document.getElementById('run').addEventListener('click', async () => {
      status.textContent = 'Preparing local policy JSON…'; status.className = 'status';
      try {
        const response = await fetch('/api/sanitize?review=' + (document.getElementById('review').checked ? '1' : '0'), {method:'POST', headers:{'Content-Type':'application/json'}, body:input.value});
        const data = await response.json(); show(data);
        status.textContent = response.ok ? 'Completed locally' : 'Input or processing error'; status.className = response.ok ? 'status success' : 'status error';
      } catch (error) { show({error:String(error)}); status.textContent = 'Could not contact the local UI'; status.className = 'status error'; }
    });
  </script>
</body>
</html>"""


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
        if self.path in {"/", "/index.html"}:
            self._send(HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        self._send(b"Not found", "text/plain; charset=utf-8", 404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] != "/api/sanitize":
            self._send(b"Not found", "text/plain; charset=utf-8", 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 2_000_000:
                raise ValueError("JSON body must be between 1 byte and 2 MB")
            request = json.loads(self.rfile.read(length).decode("utf-8"))
            query = parse_qs(urlparse(self.path).query)
            review = query.get("review", ["1"])[0] == "1"
            result = prepare_document(
                request,
                self.db_path,
                include_review_candidates=review,
            )
            body = json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")
            self._send(body, "application/json; charset=utf-8")
        except json.JSONDecodeError as exc:
            self._send(json.dumps({"error": f"INVALID_JSON: {exc.msg}"}).encode("utf-8"), "application/json; charset=utf-8", 400)
        except ValueError as exc:
            self._send(json.dumps({"error": str(exc)}).encode("utf-8"), "application/json; charset=utf-8", 400)
        except Exception as exc:
            self._send(json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8"), "application/json; charset=utf-8", 500)

    def log_message(self, format: str, *args) -> None:
        print(f"[document-ui] {self.address_string()} - {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "data/processed/finaira_generalization.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    if not args.db.exists():
        raise SystemExit(f"Database not found: {args.db}")
    Handler.db_path = args.db
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Finaira Document Sanitizer UI: http://{args.host}:{args.port}/")
    print(f"Database: {args.db}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping UI")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

