"""Strict configuration and bearer authentication for remote MCP access.

The ASGI wrapper forwards lifespan unchanged, so FastMCP retains ownership of
its Streamable HTTP session manager. It does not buffer streaming responses.
"""

from __future__ import annotations

import hmac
import ipaddress
import os
import re
from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import urlsplit


@dataclass(frozen=True)
class TransportSettings:
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8420
    api_key: str = field(default="", repr=False)
    public_origin: str = ""
    disabled_tools: tuple[str, ...] = ()


def load_settings(environ: Mapping[str, str] | None = None) -> TransportSettings:
    """Validate operator configuration before a listener or tools can run."""
    env = os.environ if environ is None else environ
    transport = env.get("OBSIDIAN_MCP_TRANSPORT", "stdio").strip()
    if transport not in {"stdio", "streamable-http"}:
        raise ValueError("OBSIDIAN_MCP_TRANSPORT must be stdio or streamable-http")

    raw_disabled = env.get("OBSIDIAN_MCP_DISABLED_TOOLS", "").strip()
    disabled = tuple(part.strip() for part in raw_disabled.split(",")) if raw_disabled else ()
    if any(not re.fullmatch(r"obsidian_[a-z_]+", name) for name in disabled):
        raise ValueError("OBSIDIAN_MCP_DISABLED_TOOLS must be comma-separated tool names")

    # HTTP-only settings have no effect on the original local stdio transport.
    if transport == "stdio":
        return TransportSettings(disabled_tools=disabled)

    host = env.get("OBSIDIAN_MCP_HOST", "127.0.0.1").strip()
    try:
        is_loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback = False
    if not is_loopback:
        raise ValueError("OBSIDIAN_MCP_HOST must be a literal loopback IP address")

    raw_port = env.get("OBSIDIAN_MCP_PORT", "8420").strip()
    if not re.fullmatch(r"[0-9]{1,5}", raw_port) or not 1 <= int(raw_port) <= 65535:
        raise ValueError("OBSIDIAN_MCP_PORT must be an integer from 1 to 65535")

    key = env.get("OBSIDIAN_MCP_API_KEY", "")
    if not key or any(ord(char) < 33 or ord(char) > 126 for char in key):
        raise ValueError("OBSIDIAN_MCP_API_KEY is required and must be visible ASCII without spaces")
    if env.get("OBSIDIAN_MCP_REQUIRE_READ_HASH", "1").strip() != "1":
        raise ValueError("HTTP mode requires OBSIDIAN_MCP_REQUIRE_READ_HASH=1")

    public_origin = env.get("OBSIDIAN_MCP_PUBLIC_URL", "").strip()
    if public_origin:
        try:
            parsed = urlsplit(public_origin)
            host_labels = (parsed.hostname or "").split(".")
            valid_hostname = all(
                re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                for label in host_labels
            ) and len(parsed.hostname or "") <= 253
            valid_origin = (
                parsed.scheme == "https"
                and valid_hostname
                and parsed.username is None
                and parsed.password is None
                and parsed.port in (None, 443)
                and parsed.netloc.lower() in {parsed.hostname, (parsed.hostname or "") + ":443"}
                and parsed.path in ("", "/")
                and not parsed.query
                and not parsed.fragment
            )
        except ValueError:
            valid_origin = False
        if not valid_origin:
            raise ValueError("OBSIDIAN_MCP_PUBLIC_URL must be an HTTPS origin without a path")
        public_origin = "https://" + parsed.hostname

    return TransportSettings(
        transport=transport,
        host=host,
        port=int(raw_port),
        api_key=key,
        public_origin=public_origin,
        disabled_tools=disabled,
    )


def disable_tools(mcp, requested: tuple[str, ...], known_tools: frozenset[str]) -> None:
    """Reject misspelled policy before removing any tool from discovery/calls."""
    unknown = set(requested) - known_tools
    if unknown:
        raise ValueError("OBSIDIAN_MCP_DISABLED_TOOLS contains an unknown tool name")
    for name in sorted(set(requested)):
        mcp.remove_tool(name)


class BearerAuthASGI:
    """Authenticate all HTTP requests except the content-free health probe."""

    def __init__(self, app, api_key: str):
        if not api_key or any(ord(char) < 33 or ord(char) > 126 for char in api_key):
            raise ValueError("HTTP bearer authentication requires a visible ASCII API key")
        self.app = app
        self._key = api_key.encode("ascii")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("path") == "/health" and scope.get("method") in {"GET", "HEAD"}:
            await self._respond(scope, send, 200, b'{"status":"ok"}')
            return

        values = [
            value for name, value in scope.get("headers", ())
            if name.lower() == b"authorization"
        ]
        authorized = False
        if len(values) == 1:
            scheme, separator, token = values[0].partition(b" ")
            # Compare bytes, not strings: malformed/non-ASCII headers must not
            # raise compare_digest's non-ASCII-string TypeError.
            authorized = (
                scheme.lower() == b"bearer"
                and bool(separator)
                and hmac.compare_digest(token, self._key)
            )
        if not authorized:
            await self._respond(scope, send, 401, b'{"error":"unauthorized"}')
            return
        await self.app(scope, receive, send)

    @staticmethod
    async def _respond(scope, send, status: int, body: bytes):
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
            (b"cache-control", b"no-store"),
        ]
        if status == 401:
            headers.append((b"www-authenticate", b"Bearer"))
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({
            "type": "http.response.body",
            "body": b"" if scope.get("method") == "HEAD" else body,
        })


def security_settings(settings: TransportSettings):
    """Retain DNS rebinding protection while permitting the configured TLS proxy."""
    from mcp.server.transport_security import TransportSecuritySettings

    hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
    bind_host = "[" + settings.host + "]" if ":" in settings.host else settings.host
    hosts.append(bind_host + ":*")
    origins.append("http://" + bind_host + ":*")
    if settings.public_origin:
        public_host = urlsplit(settings.public_origin).hostname
        hosts.extend([public_host, public_host + ":443"])
        origins.append(settings.public_origin)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


def create_http_app(mcp, settings: TransportSettings):
    """Wrap FastMCP's app without replacing or nesting its lifespan."""
    if settings.transport != "streamable-http":
        raise ValueError("The HTTP app requires streamable-http transport")
    return BearerAuthASGI(mcp.streamable_http_app(), settings.api_key)


def run_http(mcp, settings: TransportSettings) -> None:
    import uvicorn

    uvicorn.run(
        create_http_app(mcp, settings),
        host=settings.host,
        port=settings.port,
        proxy_headers=False,
        access_log=False,
    )
