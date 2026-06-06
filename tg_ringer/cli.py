"""Command-line interface for tg-ringer.

Commands:
    tg-ringer login                 one-time interactive login (phone + code)
    tg-ringer call  TARGET [-s N]   ring a user/number for N seconds
    tg-ringer msg   TARGET TEXT     send a direct message
    tg-ringer whoami                show the logged-in userbot account

Config (env vars, or ~/.config/tg-ringer/config as KEY=VALUE lines):
    TG_API_ID      required
    TG_API_HASH    required
    TG_SESSION     session file path (default ~/.config/tg-ringer/userbot)
    TG_TARGET      default target for call/msg when none is given
    RING_SECONDS   default ring duration (default 20)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

CONFIG_DIR = Path(
    os.environ.get("TG_RINGER_HOME", Path.home() / ".config" / "tg-ringer")
)
CONFIG_FILE = CONFIG_DIR / "config"


def _load_config() -> None:
    """Load KEY=VALUE lines from the config file into os.environ (no override)."""
    if not CONFIG_FILE.exists():
        return
    for line in CONFIG_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def _creds() -> tuple[int, str]:
    _load_config()
    try:
        return int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"]
    except KeyError:
        sys.exit(
            "missing TG_API_ID / TG_API_HASH (env or config file). "
            "Get them at https://my.telegram.org"
        )


def _session() -> str:
    sess = os.environ.get("TG_SESSION")
    if sess:
        return sess
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return str(CONFIG_DIR / "userbot")


def _target(arg: str | None) -> str:
    t = arg or os.environ.get("TG_TARGET")
    if not t:
        sys.exit("no target: pass one or set TG_TARGET")
    return t


def cmd_login(_args) -> None:
    # Telethon's sync context manager runs the interactive login (phone, code,
    # optional 2FA password) via stdin prompts.
    from telethon.sync import TelegramClient

    api_id, api_hash = _creds()
    with TelegramClient(_session(), api_id, api_hash) as client:
        me = client.get_me()
        print(f"Logged in as {me.first_name} (id {me.id}, @{me.username})")
        print(f"Session: {_session()}.session")


def _run(coro):
    from .client import TgCaller

    api_id, api_hash = _creds()

    async def runner():
        async with TgCaller(api_id, api_hash, _session()) as tg:
            return await coro(tg)

    return asyncio.run(runner())


def cmd_call(args) -> None:
    target = _target(args.target)
    seconds = args.seconds or int(os.environ.get("RING_SECONDS", "20"))

    async def go(tg):
        print(f"ringing {target} for {seconds}s ...")
        cid = await tg.ring(target, seconds=seconds)
        print(f"done (call id {cid})")

    _run(go)


def cmd_msg(args) -> None:
    target = _target(args.target)
    text = " ".join(args.text) if args.text else sys.stdin.read()

    async def go(tg):
        mid = await tg.message(target, text)
        print(f"sent (msg id {mid})")

    _run(go)


def cmd_whoami(_args) -> None:
    async def go(tg):
        me = await tg.whoami()
        print(f"{me.first_name} (id {me.id}, @{me.username})")

    _run(go)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(
        prog="tg-ringer",
        description="Ring/message Telegram users from your own account.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("login", help="one-time interactive login").set_defaults(
        func=cmd_login
    )

    pc = sub.add_parser("call", help="ring a user/number")
    pc.add_argument("target", nargs="?", help="username, id, or +phone")
    pc.add_argument("-s", "--seconds", type=int, help="ring duration")
    pc.set_defaults(func=cmd_call)

    pm = sub.add_parser("msg", help="send a direct message")
    pm.add_argument("target", help="username, id, or +phone")
    pm.add_argument("text", nargs="*", help="message text (or pipe via stdin)")
    pm.set_defaults(func=cmd_msg)

    sub.add_parser("whoami", help="show logged-in account").set_defaults(
        func=cmd_whoami
    )

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
