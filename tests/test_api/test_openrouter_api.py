import importlib
import os
import sys


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)


def _client_with_env(monkeypatch):
    app_module = importlib.import_module("app")
    app_module.app.config["TESTING"] = True
    return app_module, app_module.app.test_client()


def test_openrouter_status_not_configured(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    app_module, client = _client_with_env(monkeypatch)
    rv = client.get("/api/llm/openrouter/status")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["available"] is True
    assert data["configured"] is False
    assert "default_model" in data
    assert "base_url" in data


def test_openrouter_chat_requires_query_or_messages(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-v1-fake-key")
    app_module, client = _client_with_env(monkeypatch)
    rv = client.post("/api/llm/openrouter/chat", json={})
    assert rv.status_code == 400
    data = rv.get_json()
    assert "error" in data


def test_openrouter_chat_success_with_query(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-v1-fake-key")
    app_module, client = _client_with_env(monkeypatch)

    def _fake_chat_completion(**kwargs):
        assert kwargs.get("messages")
        return {
            "text": "Merhaba! Test cevabi.",
            "model": "google/gemma-3-27b-it:free",
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            "id": "test-openrouter-id",
            "tried_models": ["google/gemma-3-27b-it:free"],
        }

    monkeypatch.setattr(app_module, "openrouter_chat_completion_with_fallback", _fake_chat_completion, raising=False)

    rv = client.post("/api/llm/openrouter/chat", json={"query": "Merhaba"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert data["text"] == "Merhaba! Test cevabi."
    assert data["model"] == "google/gemma-3-27b-it:free"


def test_openrouter_chat_stream_requires_query_or_messages(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-v1-fake-key")
    app_module, client = _client_with_env(monkeypatch)
    rv = client.post("/api/llm/openrouter/chat/stream", json={})
    assert rv.status_code == 400
    data = rv.get_json()
    assert "error" in data


def test_openrouter_chat_stream_success(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-v1-fake-key")
    app_module, client = _client_with_env(monkeypatch)

    def _fake_stream(**kwargs):
        yield {"type": "token", "text": "Merhaba"}
        yield {"type": "token", "text": " dunya"}
        yield {"type": "meta", "model": "google/gemma-3-27b-it:free", "usage": {"total_tokens": 5}}
        yield {"type": "done"}

    # The stream endpoint calls openrouter_chat_completion_stream directly
    # (not the _with_fallback variant) and manages its own fallback loop.
    monkeypatch.setattr(app_module, "openrouter_chat_completion_stream", _fake_stream, raising=False)
    monkeypatch.setattr(app_module, "is_openrouter_configured", lambda: True, raising=False)
    monkeypatch.setattr(app_module, "openrouter_status", lambda: {"default_model": "google/gemma-3-27b-it:free"}, raising=False)
    monkeypatch.setattr(app_module, "record_llm_attempt", lambda **kw: None, raising=False)
    monkeypatch.setattr(app_module, "is_model_blocked", lambda provider, model: False, raising=False)

    rv = client.post("/api/llm/openrouter/chat/stream", json={"query": "selam"})
    assert rv.status_code == 200
    assert rv.mimetype == "application/x-ndjson"

    text = rv.data.decode("utf-8")
    assert '"type": "token"' in text
    assert "Merhaba" in text
    assert '"type": "done"' in text
