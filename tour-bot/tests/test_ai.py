"""ClaudeAI.answer against a local fake Messages API: tool loop, lead capture, request shape."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from bot.ai import ClaudeAI


def _message(content, stop_reason):
    return {
        "id": "msg", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
        "content": content, "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


@pytest.fixture
def fake_api():
    requests, replies = [], []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["content-length"]))))
            body = json.dumps(replies.pop(0)).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}", requests, replies
    server.shutdown()


async def test_answer_runs_tool_loop_and_captures_lead(fake_api, monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    url, requests, replies = fake_api
    replies += [
        _message(
            [{"type": "tool_use", "id": "tu1", "name": "notify_manager",
              "input": {"summary": "Dubay, 2 kishi", "phone": "+998901234567"}}],
            "tool_use",
        ),
        _message([{"type": "text", "text": "Menejer siz bilan bog'lanadi."}], "end_turn"),
    ]
    ai = ClaudeAI("test-key", "claude-opus-5-5")
    ai.client = ai.client.with_options(base_url=url, max_retries=0)

    result = await ai.answer("uz", [], "Dubayga 2 kishi boramiz, +998901234567")

    assert result.reply == "Menejer siz bilan bog'lanadi."
    assert result.is_lead and result.phone == "+998901234567" and result.lead_summary == "Dubay, 2 kishi"
    first, second = requests
    assert {t["name"] for t in first["tools"]} == {"web_search", "notify_manager"}
    assert "catalog" not in first["system"].lower()
    assert second["messages"][-1]["content"][0] == {"type": "tool_result", "tool_use_id": "tu1", "content": "Sent to the manager."}
