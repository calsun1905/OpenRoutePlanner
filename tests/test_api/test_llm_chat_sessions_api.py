import importlib
import os
import sys


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)


def _client(monkeypatch):
    app_module = importlib.import_module("app")
    app_module.app.config["TESTING"] = True
    return app_module, app_module.app.test_client()


def test_chat_session_endpoints(monkeypatch):
    app_module, client = _client(monkeypatch)

    monkeypatch.setattr(
        app_module,
        "list_chat_sessions",
        lambda include_archived=False, limit=200: [
            {
                "id": "s-1",
                "title": "Test",
                "created_at": "2026-03-24T00:00:00Z",
                "updated_at": "2026-03-24T00:00:00Z",
                "archived": 0,
                "message_count": 2,
            }
        ],
        raising=False,
    )
    monkeypatch.setattr(
        app_module,
        "create_chat_session",
        lambda title=None: {
            "id": "s-new",
            "title": title or "Yeni Sohbet",
            "created_at": "2026-03-24T00:00:00Z",
            "updated_at": "2026-03-24T00:00:00Z",
            "archived": 0,
            "message_count": 0,
        },
        raising=False,
    )
    monkeypatch.setattr(app_module, "get_chat_session", lambda session_id: {"id": session_id, "archived": 0}, raising=False)
    monkeypatch.setattr(
        app_module,
        "list_chat_messages",
        lambda session_id, limit=None: [{"id": "m1", "session_id": session_id, "role": "user", "content": "merhaba"}],
        raising=False,
    )
    monkeypatch.setattr(app_module, "archive_chat_session", lambda session_id: True, raising=False)

    rv_list = client.get("/api/llm/chat/sessions")
    assert rv_list.status_code == 200
    assert rv_list.get_json()["ok"] is True
    assert rv_list.get_json()["sessions"][0]["id"] == "s-1"

    rv_create = client.post("/api/llm/chat/sessions", json={"title": "Yeni Test"})
    assert rv_create.status_code == 201
    assert rv_create.get_json()["session"]["id"] == "s-new"

    rv_messages = client.get("/api/llm/chat/sessions/s-1/messages")
    assert rv_messages.status_code == 200
    assert rv_messages.get_json()["messages"][0]["role"] == "user"

    rv_archive = client.post("/api/llm/chat/sessions/s-1/archive")
    assert rv_archive.status_code == 200
    assert rv_archive.get_json()["archived"] is True


def test_openrouter_stream_session_persist_and_context_window(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-v1-fake-key")
    app_module, client = _client(monkeypatch)

    captured = {"save_called": False, "limit_seen": None, "messages_sent": None}

    monkeypatch.setattr(
        app_module,
        "get_chat_session",
        lambda session_id: {
            "id": session_id,
            "archived": 0,
            "title": "Test Session",
            "message_count": 6,
        },
        raising=False,
    )

    def _fake_list_chat_messages(session_id, limit=None):
        captured["limit_seen"] = limit
        return [
            {"role": "user", "content": f"u-{i}"}
            if i % 2 == 0
            else {"role": "assistant", "content": f"a-{i}"}
            for i in range(40)
        ]

    monkeypatch.setattr(app_module, "list_chat_messages", _fake_list_chat_messages, raising=False)

    def _fake_stream(**kwargs):
        captured["messages_sent"] = kwargs.get("messages")
        yield {"type": "token", "text": "Merhaba"}
        yield {"type": "meta", "model": "nvidia/nemotron-3-super-120b-a12b:free", "usage": {"total_tokens": 12}}
        yield {"type": "done"}

    # The stream endpoint calls openrouter_chat_completion_stream directly
    # (not the _with_fallback variant) and manages its own fallback loop.
    monkeypatch.setattr(app_module, "openrouter_chat_completion_stream", _fake_stream, raising=False)
    monkeypatch.setattr(app_module, "is_openrouter_configured", lambda: True, raising=False)
    monkeypatch.setattr(app_module, "openrouter_status", lambda: {"default_model": "nvidia/nemotron-3-super-120b-a12b:free"}, raising=False)
    monkeypatch.setattr(app_module, "record_llm_attempt", lambda **kw: None, raising=False)
    monkeypatch.setattr(app_module, "is_model_blocked", lambda provider, model: False, raising=False)

    def _fake_save_turn(**kwargs):
        captured["save_called"] = True
        assert kwargs["session_id"] == "sess-123"
        assert kwargs["user_text"] == "selam"
        assert "Merhaba" in kwargs["assistant_text"]
        assert kwargs["token_total"] == 12

    monkeypatch.setattr(app_module, "save_chat_turn", _fake_save_turn, raising=False)

    rv = client.post("/api/llm/openrouter/chat/stream", json={"session_id": "sess-123", "query": "selam"})
    assert rv.status_code == 200
    assert rv.mimetype == "application/x-ndjson"

    body = rv.data.decode("utf-8")
    assert '"type": "token"' in body
    assert '"type": "done"' in body
    assert captured["save_called"] is True
    assert captured["limit_seen"] == 40
    assert captured["messages_sent"][-1]["role"] == "user"
    assert captured["messages_sent"][-1]["content"] == "selam"

