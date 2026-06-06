"""Command-line interface for tg-ringer.

Commands:
    tg-ringer init                  interactive setup (saves api_id/api_hash/target)
    tg-ringer login                 set up (if needed) + log the userbot in
    tg-ringer call  TARGET [-s N]   ring a user/number for N seconds
    tg-ringer msg   TARGET TEXT     send a direct message
    tg-ringer whoami                show the logged-in userbot account
    tg-ringer status                check anti-spam status via @SpamBot
    tg-ringer config                show current config (api_hash masked)

Config is read from (first wins): environment variables, then
``~/.config/tg-ringer/config`` (KEY=VALUE lines). Keys:
    TG_API_ID, TG_API_HASH   required (set once via `init`/`login`)
    TG_SESSION               session file path (default ~/.config/tg-ringer/userbot)
    TG_TARGET                default target for call/msg
    RING_SECONDS             default ring duration (default 20)
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


def _save_config(values: dict[str, str]) -> None:
    """Write/merge KEY=VALUE pairs into the config file (chmod 600)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    existing: dict[str, str] = {}
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()
    existing.update({k: v for k, v in values.items() if v})
    body = "# tg-ringer config — keep private (contains api_hash)\n"
    body += "\n".join(f"{k}={v}" for k, v in existing.items()) + "\n"
    CONFIG_FILE.write_text(body)
    CONFIG_FILE.chmod(0o600)


def _is_configured() -> bool:
    _load_config()
    return bool(os.environ.get("TG_API_ID") and os.environ.get("TG_API_HASH"))


def _interactive_setup() -> None:
    """Prompt for credentials and save them. Safe to re-run."""
    print("tg-ringer setup — get api_id/api_hash at https://my.telegram.org\n")
    api_id = input("api_id  : ").strip()
    api_hash = input("api_hash: ").strip()
    target = input("default target (optional, e.g. +15551234567): ").strip()
    if not api_id or not api_hash:
        sys.exit("api_id and api_hash are required")
    values = {"TG_API_ID": api_id, "TG_API_HASH": api_hash}
    if target:
        values["TG_TARGET"] = target
    _save_config(values)
    _load_config()  # refresh process env
    print(f"\nSaved to {CONFIG_FILE}")


def _creds() -> tuple[int, str]:
    if not _is_configured():
        sys.exit("not configured — run `tg-ringer init` (or `tg-ringer login`)")
    return int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"]


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


def cmd_init(_args) -> None:
    _interactive_setup()
    print("Next: run `tg-ringer login` to sign the userbot in.")


def cmd_config(_args) -> None:
    _load_config()
    api_hash = os.environ.get("TG_API_HASH", "")
    masked = (api_hash[:4] + "…" + api_hash[-4:]) if len(api_hash) > 8 else "(unset)"
    exists = "exists" if CONFIG_FILE.exists() else "none"
    print(f"config file : {CONFIG_FILE} ({exists})")
    print(f"TG_API_ID   : {os.environ.get('TG_API_ID', '(unset)')}")
    print(f"TG_API_HASH : {masked}")
    print(f"TG_TARGET   : {os.environ.get('TG_TARGET', '(unset)')}")
    print(f"TG_SESSION  : {_session()}.session")
    print(f"RING_SECONDS: {os.environ.get('RING_SECONDS', '20')}")


def cmd_login(_args) -> None:
    # First-run friendly: if not configured, walk through setup.
    if not _is_configured():
        _interactive_setup()
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


def cmd_status(_args) -> None:
    async def go(tg):
        print("asking @SpamBot ...")
        reply = await tg.spam_status()
        print("---")
        print(reply)

    _run(go)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(
        prog="tg-ringer",
        description="Ring/message Telegram users from your own account.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="interactive setup (save credentials)").set_defaults(
        func=cmd_init
    )
    sub.add_parser(
        "login", help="set up (if needed) + log the userbot in"
    ).set_defaults(func=cmd_login)
    sub.add_parser("config", help="show current config").set_defaults(func=cmd_config)

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
    sub.add_parser("status", help="check anti-spam status via @SpamBot").set_defaults(
        func=cmd_status
    )

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
