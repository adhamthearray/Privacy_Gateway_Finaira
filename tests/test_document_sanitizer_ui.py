import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.run_document_sanitizer_ui import HTML, Handler


DB = "data/processed/finaira_generalization.db"


def _post(payload, *, review=True):
    Handler.db_path = DB
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        suffix = "?review=1" if review else "?review=0"
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/sanitize{suffix}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_document_ui_has_drop_zone_and_json_output():
    assert "Drop a" in HTML
    assert 'id="file"' in HTML
    assert 'id="output"' in HTML
    assert "/api/sanitize" in HTML


def test_document_ui_returns_policy_json():
    status, result = _post({
        "document_id": "doc-001",
        "text": "[[E0001]] emailed [[E0002]].",
        "entity_map": {
            "E0001": {"label": "PERSON_NAME", "original_text": "Ahmed Ali", "placeholder": "[[E0001]]"},
            "E0002": {"label": "EMAIL_ADDRESS", "original_text": "ahmed@example.com", "placeholder": "[[E0002]]"},
        },
    })
    assert status == 200
    assert result["entities"]["E0001"]["pseudonymization_form"] == "__FN_PERSON_0001__"
    assert result["entities"]["E0002"]["pseudonymization_form"] == "__FN_EMAIL_0001__"


def test_document_ui_returns_structured_validation_error():
    status, result = _post({"document_id": "bad", "text": "hello", "entity_map": {"E1": {"label": "PERSON_NAME", "original_text": "A", "placeholder": "[[E1]]"}}})
    assert status == 400
    assert result["error"] == "PLACEHOLDER_NOT_FOUND:E1"

