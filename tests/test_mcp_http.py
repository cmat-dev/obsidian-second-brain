"""Transport configuration and real FastMCP protocol tests with synthetic keys."""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
from pathlib import Path

import pytest

SERVER_DIR = Path(__file__).resolve().parents[1] / "integrations" / "obsidian-mcp-server"
sys.path.insert(0, str(SERVER_DIR))
import http_transport  # noqa: E402

KEY = "synthetic-test-key-only"
HTTP_ENV = {
    "OBSIDIAN_MCP_TRANSPORT": "streamable-http",
    "OBSIDIAN_MCP_API_KEY": KEY,
}
CONFIG_NAMES = (
    "OBSIDIAN_MCP_TRANSPORT", "OBSIDIAN_MCP_HOST", "OBSIDIAN_MCP_PORT",
    "OBSIDIAN_MCP_API_KEY", "OBSIDIAN_MCP_PUBLIC_URL", "OBSIDIAN_MCP_DISABLED_TOOLS",
    "OBSIDIAN_MCP_REQUIRE_READ_HASH", "OBSIDIAN_MCP_ALLOW_FRONTMATTER",
    "OBSIDIAN_MCP_AGENT", "OBSIDIAN_SKILL_FLAVOR", "OBSIDIAN_TRANSACTION_HELPER",
)


def test_stdio_default_ignores_http_only_configuration():
    settings = http_transport.load_settings({
        "OBSIDIAN_MCP_HOST": "0.0.0.0", "OBSIDIAN_MCP_PORT": "bad",
        "OBSIDIAN_MCP_PUBLIC_URL": "bad", "OBSIDIAN_MCP_REQUIRE_READ_HASH": "0",
    })
    assert settings.transport == "stdio"
    assert settings.api_key == ""


def test_http_defaults_are_local_and_key_is_not_in_repr():
    settings = http_transport.load_settings(HTTP_ENV)
    assert (settings.host, settings.port) == ("127.0.0.1", 8420)
    assert KEY not in repr(settings)


@pytest.mark.parametrize("name,value", [
    ("OBSIDIAN_MCP_TRANSPORT", "sse"),
    ("OBSIDIAN_MCP_API_KEY", ""),
    ("OBSIDIAN_MCP_API_KEY", "with spaces"),
    ("OBSIDIAN_MCP_API_KEY", "non-ascii-\u00e9"),
    ("OBSIDIAN_MCP_API_KEY", "line\nfeed"),
    ("OBSIDIAN_MCP_HOST", "0.0.0.0"),
    ("OBSIDIAN_MCP_HOST", "::"),
    ("OBSIDIAN_MCP_HOST", "localhost"),
    ("OBSIDIAN_MCP_HOST", "192.0.2.1"),
    ("OBSIDIAN_MCP_PORT", "0"),
    ("OBSIDIAN_MCP_PORT", "65536"),
    ("OBSIDIAN_MCP_PORT", "8.4"),
    ("OBSIDIAN_MCP_PORT", "+8420"),
    ("OBSIDIAN_MCP_PORT", "\u0668\u0664\u0662\u0660"),
    ("OBSIDIAN_MCP_REQUIRE_READ_HASH", "0"),
    ("OBSIDIAN_MCP_DISABLED_TOOLS", "obsidian_move_note,"),
    ("OBSIDIAN_MCP_PUBLIC_URL", "http://example.ts.net"),
    ("OBSIDIAN_MCP_PUBLIC_URL", "https://user:password@example.ts.net"),
    ("OBSIDIAN_MCP_PUBLIC_URL", "https://example.ts.net/mcp"),
    ("OBSIDIAN_MCP_PUBLIC_URL", "https://example.ts.net?key=value"),
    ("OBSIDIAN_MCP_PUBLIC_URL", "https://example.ts.net:1234"),
    ("OBSIDIAN_MCP_PUBLIC_URL", "https://example.ts.net:"),
    ("OBSIDIAN_MCP_PUBLIC_URL", "https://*.ts.net"),
])
def test_invalid_http_configuration_refuses_start(name, value):
    with pytest.raises(ValueError, match=name):
        http_transport.load_settings({**HTTP_ENV, name: value})


def test_unknown_disabled_tool_fails_before_policy_mutation():
    removed = []

    class FakeMCP:
        def remove_tool(self, name):
            removed.append(name)

    with pytest.raises(ValueError, match="unknown"):
        http_transport.disable_tools(
            FakeMCP(), ("obsidian_move_note", "obsidian_missing"),
            frozenset({"obsidian_move_note"}),
        )
    assert removed == []


def test_public_https_default_port_is_normalized():
    settings = http_transport.load_settings({
        **HTTP_ENV, "OBSIDIAN_MCP_PUBLIC_URL": "https://Example.ts.net:443/",
    })
    assert settings.public_origin == "https://example.ts.net"


@pytest.fixture()
def server_factory(tmp_path, monkeypatch):
    pytest.importorskip("mcp.server.fastmcp", reason="Install mcp<2 for live protocol tests")
    root = tmp_path / "vault"
    root.mkdir()
    (root / "note.md").write_text("Synthetic vault content.\n", encoding="utf-8")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(root))
    for name in CONFIG_NAMES:
        monkeypatch.delenv(name, raising=False)

    def make(**overrides):
        for name in CONFIG_NAMES:
            monkeypatch.delenv(name, raising=False)
        for name, value in {**HTTP_ENV, **overrides}.items():
            monkeypatch.setenv(name, value)
        import server
        return importlib.reload(server)

    return make


def _client(server):
    from starlette.testclient import TestClient

    app = http_transport.create_http_app(server.mcp, server.settings)
    return TestClient(app, base_url="http://127.0.0.1:8420")


def _headers(key=KEY):
    return {
        "Authorization": "Bearer " + key,
        "Accept": "application/json, text/event-stream",
    }


def _message(response):
    response.raise_for_status()
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    for line in response.text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    raise AssertionError("MCP response contained no JSON-RPC message")


def _initialize(client, **extra_headers):
    headers = {**_headers(), **extra_headers}
    response = client.post("/mcp", headers=headers, json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "synthetic-test-client", "version": "1"},
        },
    })
    result = _message(response)["result"]
    session_id = response.headers["mcp-session-id"]
    headers.update({
        "Mcp-Session-Id": session_id,
        "Mcp-Protocol-Version": result["protocolVersion"],
    })
    initialized = client.post("/mcp", headers=headers, json={
        "jsonrpc": "2.0", "method": "notifications/initialized",
    })
    assert initialized.status_code == 202
    return headers


def test_health_is_content_free_without_credentials(server_factory):
    server = server_factory()
    with _client(server) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert "vault" not in response.text.lower()
        assert KEY not in response.text
        assert client.head("/health").content == b""
        assert client.post("/health").status_code == 401


@pytest.mark.parametrize("headers", [
    {}, {"Authorization": "Bearer wrong"}, {"Authorization": "Basic " + KEY},
    {"Authorization": "Bearer"}, {"Authorization": "Bearer " + KEY + " "},
])
def test_unauthenticated_requests_never_reach_mcp(server_factory, headers):
    server = server_factory()
    with _client(server) as client:
        # Deliberately invalid JSON would fail differently if MCP saw it.
        response = client.post("/mcp", headers=headers, content=b"not-json")
        assert response.status_code == 401
        assert response.json() == {"error": "unauthorized"}
        assert response.headers["www-authenticate"] == "Bearer"
        assert client.get("/mcp", headers=headers).status_code == 401


@pytest.mark.parametrize("values", [
    [b"Bearer \xff\xfe"], ["Bearer \u00e9".encode("utf-8")],
    [b"Bearer " + KEY.encode(), b"Bearer " + KEY.encode()],
    [b"Bearer " + KEY.encode() + b"\x00"],
])
def test_malformed_or_duplicate_headers_fail_safely(values):
    called = []
    responses = []

    async def downstream(scope, receive, send):
        called.append(True)

    async def send(message):
        responses.append(message)

    app = http_transport.BearerAuthASGI(downstream, KEY)
    asyncio.run(app({
        "type": "http", "path": "/mcp", "method": "POST",
        "headers": [(b"authorization", value) for value in values],
    }, None, send))
    assert not called
    assert responses[0]["status"] == 401


def test_live_tools_list_and_disabled_call_with_session_lifespan(server_factory):
    server = server_factory(OBSIDIAN_MCP_DISABLED_TOOLS="obsidian_move_note")
    assert os.environ["OBSIDIAN_MCP_REQUIRE_READ_HASH"] == "1"
    with _client(server) as client:
        headers = _initialize(client)
        response = client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list",
        })
        tools = {tool["name"]: tool for tool in _message(response)["result"]["tools"]}
        assert set(tools) == server.TOOL_NAMES - {"obsidian_move_note"}
        for name in ("obsidian_update_note", "obsidian_replace_text"):
            assert "expected_sha256" in tools[name]["inputSchema"]["properties"]
        disabled = client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {
                "name": "obsidian_move_note",
                "arguments": {"source": "note.md", "destination": "moved.md"},
            },
        })
        assert _message(disabled)["result"]["isError"] is True
        # Session possession does not bypass bearer authentication.
        unauthorized_headers = {key: value for key, value in headers.items() if key != "Authorization"}
        assert client.post("/mcp", headers=unauthorized_headers, json={
            "jsonrpc": "2.0", "id": 4, "method": "tools/list",
        }).status_code == 401


def test_public_origin_is_allowlisted_without_disabling_host_checks(server_factory):
    server = server_factory(OBSIDIAN_MCP_PUBLIC_URL="https://synthetic.tailnet.ts.net")
    with _client(server) as client:
        headers = _initialize(client, Host="synthetic.tailnet.ts.net", Origin="https://synthetic.tailnet.ts.net")
        assert client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list",
        }).status_code == 200
        refused = client.post("/mcp", headers={**headers, "Host": "other.example"}, json={
            "jsonrpc": "2.0", "id": 3, "method": "tools/list",
        })
        assert refused.status_code == 421


def test_invalid_disabled_name_refuses_server_start(server_factory):
    with pytest.raises(ValueError, match="unknown tool"):
        server_factory(OBSIDIAN_MCP_DISABLED_TOOLS="obsidian_mvoe_note")


def test_real_stdio_handshake_still_works_without_http_key(tmp_path):
    pytest.importorskip("mcp", reason="Install mcp<2 for live protocol tests")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root = tmp_path / "stdio-vault"
    root.mkdir()
    (root / "note.md").write_bytes(b"Synthetic stdio note.\n")
    env = {name: value for name, value in os.environ.items() if name not in CONFIG_NAMES}
    env.update({"OBSIDIAN_VAULT_PATH": str(root), "PYTHONIOENCODING": "utf-8"})

    async def round_trip():
        parameters = StdioServerParameters(
            command=sys.executable, args=[str(SERVER_DIR / "server.py")], env=env,
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert len(tools.tools) == 12
                assert "obsidian_move_note" in {tool.name for tool in tools.tools}
                result = await session.call_tool("obsidian_read_note", {"path": "note.md"})
                assert not result.isError
                assert json.loads(result.content[0].text)["content"] == "Synthetic stdio note.\n"

    asyncio.run(asyncio.wait_for(round_trip(), timeout=20))
