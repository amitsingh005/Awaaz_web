import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.browser import trim_page_text, perform_search
from app.services.summarizer import summarize_findings

client = TestClient(app)

def test_trim_page_text():
    html_sample = "<div><h1>Train Schedule</h1><p>Express 1234  runs daily  from Delhi to Bhopal.</p><script>var x=1;</script></div>"
    trimmed = trim_page_text(html_sample, max_chars=100)
    assert "<" not in trimmed
    assert ">" not in trimmed
    assert "Train Schedule" in trimmed
    assert "Express 1234" in trimmed
    assert len(trimmed) <= 100 + len("... [trimmed]")

def test_live_search_and_summarizer():
    # 1. Search
    results = perform_search("Delhi to Bhopal train timing", max_results=3)
    assert len(results) > 0
    assert "title" in results[0]
    assert "snippet" in results[0]

    # 2. Summarize
    summary = summarize_findings("Delhi se Bhopal train dhundho", results)
    assert len(summary.reply_text) > 0
    assert isinstance(summary.options, list)
    assert len(summary.options) <= 4

def test_e2e_text_readonly_flow():
    # 1. Create session
    sess_res = client.post("/api/session")
    session_id = sess_res.json()["session_id"]

    # 2. Send read-only query
    res = client.post(
        "/api/text",
        json={"session_id": session_id, "text": "Delhi se Bhopal ki train dhundho"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["state"] == "done"
    assert len(data["reply_text"]) > 0
    assert len(data["options"]) > 0
    assert any("search" in n.lower() or "mode" in n.lower() for n in data["narration"])

    # 3. Test 'dobara bolo' command
    repeat_res = client.post(
        "/api/text",
        json={"session_id": session_id, "text": "dobara bolo"},
    )
    assert repeat_res.status_code == 200
    repeat_data = repeat_res.json()
    assert data["reply_text"] in repeat_data["reply_text"]
