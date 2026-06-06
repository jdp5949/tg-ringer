"""tg-caller — ring and message any Telegram user from your own account (userbot).

Account-to-account (MTProto), not a bot. The userbot places a real private
Telegram call so the target's phone *rings* (use as an urgent alert), or sends
a direct message.

Basic use:

    import asyncio
    from tg_caller import TgCaller

    async def main():
        async with TgCaller(api_id, api_hash, "userbot") as tg:
            await tg.ring("+15551234567", seconds=20)
            await tg.message("+15551234567", "heads up")

    asyncio.run(main())
"""
from .client import TgCaller

__all__ = ["TgCaller"]
__version__ = "0.1.0"
