# tg-ringer

Ring (call) and message **any Telegram user from your own account** — a lightweight
[Telethon](https://github.com/LonamiWebs/Telethon) userbot for **urgent alerts**.

It places a real **private Telegram call** so the target's phone *rings* (no audio
is streamed — the ring itself is the alert), then hangs up. It can also send direct
account-to-account messages.

> **This is a userbot (your real account), not a bot.** That is the point — bots
> cannot place calls. See [⚠️ ToS & bans](#️-tos--bans) before using.

---

## When to use it

| You want… | Use this? |
|-----------|-----------|
| Phone to **ring** on a critical event (build failed, server down, prod alert) | ✅ yes |
| A free alternative to paid call APIs, and you already live in Telegram | ✅ yes |
| Account-to-account DM from a script (faster than Bot API on a warm connection) | ✅ yes |
| Spoken/TTS audio in the call | ❌ no — ring only (see [limitations](#limitations)) |
| Reach someone with **no internet** (real cellular call) | ❌ no — Telegram is VoIP; use Twilio/PSTN |
| Mass messaging / spam | ❌ absolutely not — instant ban |

---

## Install

```bash
pip install tg-ringer
```

Requires Python 3.9+.

### Also available in other languages 🌍

| Language | Install | Downloads |
|----------|---------|-----------|
| 🐍 Python | `pip install tg-ringer` | [PyPI](https://pypi.org/project/tg-ringer/) |
| 🐹 Go | `go install github.com/jdp5949/tg-ringer-go/cmd/tg-ringer@latest` | [binaries](https://github.com/jdp5949/tg-ringer-go/releases) |
| 🟢 Node/TS | `npm install github:jdp5949/tg-ringer-js` | [tarball](https://github.com/jdp5949/tg-ringer-js/releases) |
| ☕ Java | JitPack `com.github.jdp5949:tg-ringer-java:v0.1.0` | [jars](https://github.com/jdp5949/tg-ringer-java/releases) |
| 🦀 Rust | `cargo install --git https://github.com/jdp5949/tg-ringer-rs` | [binaries](https://github.com/jdp5949/tg-ringer-rs/releases) |

Full docs & use cases: **https://jdp5949.github.io/tg-ringer/**

---

## Setup (one command)

Just run `login` — it walks you through everything the first time (no files to edit):

```bash
tg-ringer login
```

It will:
1. Prompt for your **`api_id`** / **`api_hash`** (get them at <https://my.telegram.org>
   → *API development tools*) and an optional default target, then save them to
   `~/.config/tg-ringer/config` (chmod 600).
2. Ask for the **userbot account's** phone number, the login code (delivered *inside
   Telegram*, not SMS), and a 2FA password if you have one.

Later runs skip setup and just sign in. Re-run setup anytime with `tg-ringer init`;
inspect it with `tg-ringer config`.

> Use a **separate account** as the userbot — not the one you want to ring. You
> cannot call yourself.

### Configuration values

Saved by `login`/`init`, or supplied as env vars (env takes precedence — handy in CI):

| Var | Meaning |
|-----|---------|
| `TG_API_ID`, `TG_API_HASH` | credentials (required) |
| `TG_TARGET` | default target for `call`/`msg` |
| `RING_SECONDS` | default ring duration (20) |
| `TG_SESSION` | session file path |
| `TG_RINGER_HOME` | config directory override |

---

## CLI usage

```bash
# Ring a number (or @username, or numeric id) — phone rings, then hangs up
tg-ringer call +15551234567
tg-ringer call @someuser --seconds 30
tg-ringer call                       # uses TG_TARGET

# Send a direct message
tg-ringer msg +15551234567 "deploy finished"
echo "piped body" | tg-ringer msg @someuser

# Who am I logged in as?
tg-ringer whoami
```

### In scripts

```bash
long_task && tg-ringer msg "$ALERT" "✅ done" || tg-ringer call "$ALERT"
```

---

## Library usage

```python
import asyncio
from tg_ringer import TgCaller

async def main():
    async with TgCaller(api_id=1234567, api_hash="...", session="userbot") as tg:
        await tg.ring("+15551234567", seconds=20)     # phone rings 20s
        await tg.message("+15551234567", "heads up")   # direct message

asyncio.run(main())
```

`TgCaller` methods (all async):

| Method | Does |
|--------|------|
| `ring(target, seconds=20)` | Place a private call; phone rings then hangs up. Returns call id. |
| `message(target, text)` | Send a direct message. Returns message id. |
| `resolve(target)` | Resolve a `@username`, numeric id, or `+phone` to an entity. |
| `whoami()` | Return the logged-in account. |

`target` may be a `@username`, a numeric user id, or a `+E164` phone number. A
phone number is imported as a temporary contact so it can be reached.

---

## Limitations

- **Ring only, no audio.** Playing TTS/sound needs the full encrypted call to
  connect (WebRTC/Opus). `pytgcalls` covers *group* voice chats, not private 1-to-1
  calls; private-call audio needs the old `libtgvoip` stack (fragile). For a spoken
  message, use a PSTN provider (e.g. Twilio).
- **Internet required on the receiver.** Telegram calls are VoIP.
- **Calls only land if Telegram lets them.** New accounts, and especially **VoIP
  numbers**, hit anti-spam (`PeerFloodError`). Best results when caller and target
  are **mutual contacts**.

---

## ⚠️ ToS & bans

Automating a **user** account (userbot) is a **gray area** under Telegram's Terms of
Service. Risks you accept by using this:

- Accounts can be **limited or banned**, especially VoIP numbers, new accounts, or
  any account making automated calls/messages to non-contacts.
- Keep volume low. Make the caller and target **mutual contacts**. Do **not** spam.
- Use a throwaway/secondary account as the userbot.

You are responsible for how you use this. See `@SpamBot` in Telegram to check an
account's restriction status.

---

## Security

- Your `api_hash` and the `*.session` file grant **full access to the userbot
  account**. Never commit or share them. The config and session live under
  `~/.config/tg-ringer/` and are git-ignored in this repo.
- Revoke a leaked session from any Telegram client: *Settings → Devices → Terminate*.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `PeerFloodError` | Account anti-spam limited. Make caller+target mutual contacts; check `@SpamBot`; wait; or use a non-VoIP number. |
| `session not authorized` | Run `tg-ringer login`. |
| Login code never arrives | It's delivered **in the Telegram app** ("Telegram" service chat), not SMS. The userbot number must be logged into a Telegram client. |
| Target not on Telegram | `+phone` must belong to a Telegram account. |
| No notification but message sent | Receiver chat is muted / OS notifications off. |

---

## License

MIT © jdp5949
