from pathlib import Path


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def test_frontend_streams_auditable_progress_and_can_cancel():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    script = (FRONTEND_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="stop-button"' in html
    assert "公开执行过程" in script
    assert 'fetch("/run_sse"' in script
    assert "new AbortController()" in script
    assert "state.abortController.abort()" in script
    assert "part?.thought" in script


def test_frontend_manages_persistent_conversation_history():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    script = (FRONTEND_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="conversation-history"' in html
    assert 'id="rename-dialog"' in html
    assert 'id="delete-dialog"' in html
    assert "conversation_title" in script
    assert 'method: "PATCH"' in script
    assert 'method: "DELETE"' in script
    assert "renderSessionHistory" in script
    assert 'cache: "no-store"' in script
    assert "historyRequestVersion" in script
    assert "deletedSessionIds" in script
    assert "verificationResponse" in script
