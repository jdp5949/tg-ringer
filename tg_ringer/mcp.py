"""MCP server for tg-ringer — Telegram tools for Claude Code and AI agents.

Exposes 5 tools over stdio (launch via `tg-ringer-mcp`):

    tg_ring     — ring a Telegram user (phone rings, no audio)
    tg_message  — send a DM
    tg_whoami   — show logged-in userbot account
    tg_status   — check anti-spam status via @SpamBot
    tg_ask      — send a question, block until user replies, return reply text

Claude Code config (~/.claude/settings.json):

    {
      "mcpServers": {
        "tg-ringer": {
          "command": "ssh",
          "args": ["<your-host>", "tg-ringer-mcp"]
        }
      }
    }

For local use (no SSH):
    { "mcpServers": { "tg-ringer": { "command": "tg-ringer-mcp" } } }
"""

from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Config helpers (mirrors cli.py so same config file is shared)
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(
    os.environ.get("TG_RINGER_HOME", Path.home() / ".config" / "tg-ringer")
)
_CONFIG_FILE = _CONFIG_DIR / "config"


def _load_config() -> None:
    if not _CONFIG_FILE.exists():
        return
    for line in _CONFIG_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def _creds() -> tuple[int, str]:
    _load_config()
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        raise RuntimeError("Not configured — run `tg-ringer init` on the server first")
    return int(api_id), api_hash


def _session() -> str:
    sess = os.environ.get("TG_SESSION")
    if sess:
        return sess
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return str(_CONFIG_DIR / "userbot")


def _default_target() -> str | None:
    return os.environ.get("TG_TARGET")


def _resolve_target(arg: str | None) -> str:
    t = arg or _default_target()
    if not t:
        raise ValueError("No target — pass `target` or set TG_TARGET in config")
    return t


# ---------------------------------------------------------------------------
# Singleton TgCaller (kept connected for the lifetime of the MCP process)
# ---------------------------------------------------------------------------

_caller: object | None = None  # TgCaller; avoid top-level import of telethon


@asynccontextmanager
async def _lifespan(_server: FastMCP):
    global _caller
    from tg_ringer.client import TgCaller

    api_id, api_hash = _creds()
    caller = TgCaller(api_id, api_hash, _session())
    await caller.__aenter__()  # type: ignore[attr-defined]
    _caller = caller
    try:
        yield
    finally:
        _caller = None
        await caller.__aexit__(None, None, None)  # type: ignore[attr-defined]


mcp = FastMCP("tg-ringer", lifespan=_lifespan)


def _tg():
    """Return the live TgCaller, raising clearly if not ready."""
    if _caller is None:
        raise RuntimeError("tg-ringer MCP not initialized — check session on server")
    return _caller  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def tg_ring(seconds: int = 20, target: str | None = None) -> str:
    """Ring a Telegram user so their phone rings, then hang up. Ring IS the alert.

    Args:
        seconds: How long to let it ring before hanging up (default 20).
        target: @username, numeric id, or +E164 phone. Defaults to TG_TARGET env var.
    """
    t = _resolve_target(target)
    cid = await _tg().ring(t, seconds=seconds)
    return f"Rang {t} for {seconds}s (call id {cid})"


@mcp.tool()
async def tg_message(text: str, target: str | None = None) -> str:
    """Send a Telegram direct message from the userbot account.

    Args:
        text: Message body to send.
        target: @username, numeric id, or +E164 phone. Defaults to TG_TARGET env var.
    """
    t = _resolve_target(target)
    mid = await _tg().message(t, text)
    return f"Sent to {t} (msg id {mid})"


@mcp.tool()
async def tg_whoami() -> str:
    """Return the logged-in userbot Telegram account (name, id, username)."""
    me = await _tg().whoami()
    uname = f"@{me.username}" if me.username else "(no username)"
    return f"{me.first_name} (id {me.id}, {uname})"


@mcp.tool()
async def tg_status() -> str:
    """Check this userbot account's anti-spam status via @SpamBot.

    Useful to diagnose PeerFloodError or call failures.
    """
    return await _tg().spam_status()


@mcp.tool()
async def tg_ask(
    question: str,
    timeout: int = 120,
    target: str | None = None,
) -> str:
    """Send a question to the Telegram user and wait for their reply.

    Use when you need human input to continue work:
      1. User receives the question as a Telegram DM.
      2. User types their reply in Telegram.
      3. This tool returns the reply text so you can proceed.

    Args:
        question: The question or prompt to send.
        timeout: Seconds to wait for a reply before giving up (default 120).
        target: @username, numeric id, or +E164. Defaults to TG_TARGET env var.

    Returns:
        The user's reply text.

    Raises:
        TimeoutError: If no reply arrives within `timeout` seconds.
    """
    t = _resolve_target(target)
    tg = _tg()

    # Resolve target entity (needed for message filtering)
    entity = await tg.resolve(t)

    # Send the question
    prompt = f"\U0001f916 Claude asks:\n\n{question}"
    sent = await tg.client.send_message(entity, prompt)

    # Poll for a reply using min_id so we only see messages after our question.
    # This avoids date-comparison timezone issues and the same-second miss.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        async for msg in tg.client.iter_messages(entity, limit=50, min_id=sent.id):
            if not msg.out:
                return msg.raw_text or "(empty reply)"
        await asyncio.sleep(3)

    raise TimeoutError(
        f"No reply from {t} within {timeout}s. "
        "Check Telegram and retry, or increase timeout."
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
