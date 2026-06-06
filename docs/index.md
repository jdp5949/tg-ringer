# tg-ringer

**Ring (call) and message any Telegram user from your own account.**
A tiny [Telethon](https://github.com/LonamiWebs/Telethon) userbot for **urgent alerts** —
it places a real private Telegram call so your phone *rings*, then hangs up.

[⭐ GitHub repo](https://github.com/jdp5949/tg-ringer) ·
[📦 PyPI](https://pypi.org/project/tg-ringer/)

---

## Why

Telegram **bots cannot place calls**. A *userbot* (your own account, via MTProto)
can. When a build fails or prod goes down at 3am, a silent push is easy to miss — a
**ringing phone** is not. `tg-ringer` turns any script event into a phone ring, for
free, using Telegram you already have.

---

## When to use it

✅ Phone should **ring** on a critical event (CI failure, server down, prod alert)
✅ Free alternative to paid call APIs, if you already use Telegram
✅ Account-to-account DMs from scripts

❌ Spoken/TTS audio in the call — *ring only* (use Twilio for voice)
❌ Reaching someone with **no internet** — Telegram is VoIP (use PSTN)
❌ Mass messaging / spam — instant ban

---

## Quick start

```bash
pip install tg-ringer
```

1. Get `api_id` / `api_hash` at <https://my.telegram.org>.
2. Put them in `~/.config/tg-ringer/config`:

   ```ini
   TG_API_ID=1234567
   TG_API_HASH=0123456789abcdef0123456789abcdef
   TG_TARGET=+15551234567
   ```

3. Log in once (use a **separate** account as the userbot — you can't call yourself):

   ```bash
   tg-ringer login
   ```

4. Ring it:

   ```bash
   tg-ringer call +15551234567
   tg-ringer msg  +15551234567 "deploy done"
   ```

---

## In scripts

```bash
long_task && tg-ringer msg "$ALERT" "✅ done" || tg-ringer call "$ALERT"
```

## In Python

```python
import asyncio
from tg_ringer import TgCaller

async def main():
    async with TgCaller(api_id, api_hash, "userbot") as tg:
        await tg.ring("+15551234567", seconds=20)
        await tg.message("+15551234567", "heads up")

asyncio.run(main())
```

---

## ⚠️ Heads up

- **ToS gray area.** Userbots can be **limited or banned** — especially VoIP numbers
  and new accounts placing automated calls. Keep volume low, make caller + target
  **mutual contacts**, use a throwaway account, never spam.
- **Ring only** — no audio. Receiver needs internet (Telegram is VoIP).
- `PeerFloodError`? Anti-spam limit. Mutual contacts + `@SpamBot` check + patience,
  or use a non-VoIP number.

Full docs & troubleshooting: see the
[README](https://github.com/jdp5949/tg-ringer#readme).

---

<sub>MIT © jdp5949 · This is an independent project, not affiliated with Telegram.</sub>
