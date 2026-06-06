"""Core async client: resolve targets, ring (private call), and message."""

from __future__ import annotations

import asyncio
import hashlib
import secrets

from telethon import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.functions.messages import GetDhConfigRequest
from telethon.tl.functions.phone import DiscardCallRequest, RequestCallRequest
from telethon.tl.types import (
    InputPhoneCall,
    InputPhoneContact,
    PhoneCallDiscardReasonHangup,
    PhoneCallProtocol,
)


class TgCaller:
    """Userbot wrapper around Telethon for ringing and messaging users.

    Args:
        api_id: Telegram API id (https://my.telegram.org).
        api_hash: Telegram API hash.
        session: Telethon session name or path (a ``.session`` file).
    """

    def __init__(self, api_id: int, api_hash: str, session: str = "tgcaller"):
        self.client = TelegramClient(session, api_id, api_hash)

    async def __aenter__(self) -> TgCaller:
        await self.client.connect()
        if not await self.client.is_user_authorized():
            raise RuntimeError("session not authorized — run `tg-caller login` first")
        return self

    async def __aexit__(self, *exc) -> None:
        await self.client.disconnect()

    async def resolve(self, target):
        """Resolve a username, numeric id, or +phone number to an entity.

        A ``+phone`` is imported as a temporary contact so it can be reached;
        this is what lets you ring a number you have not chatted with before.
        """
        if isinstance(target, str) and target.startswith("+"):
            res = await self.client(
                ImportContactsRequest(
                    [
                        InputPhoneContact(
                            client_id=0,
                            phone=target,
                            first_name="alert",
                            last_name="target",
                        )
                    ]
                )
            )
            if not res.users:
                raise ValueError(f"{target} is not on Telegram / not resolvable")
            return res.users[0]
        return await self.client.get_input_entity(target)

    async def ring(self, target, seconds: int = 20) -> int:
        """Place a private call so ``target``'s phone rings, then hang up.

        No audio is streamed — the *ring* is the alert. Returns the call id.
        """
        peer = await self.resolve(target)

        dh = await self.client(GetDhConfigRequest(version=0, random_length=256))
        p = int.from_bytes(dh.p, "big")
        g = dh.g
        a = int.from_bytes(secrets.token_bytes(256), "big") % p
        g_a = pow(g, a, p)
        g_a_hash = hashlib.sha256(g_a.to_bytes(256, "big")).digest()

        protocol = PhoneCallProtocol(
            min_layer=65,
            max_layer=92,
            udp_p2p=True,
            udp_reflector=True,
            library_versions=["4.0.0"],
        )
        res = await self.client(
            RequestCallRequest(
                user_id=peer,
                random_id=secrets.randbelow(2**31),
                g_a_hash=g_a_hash,
                protocol=protocol,
            )
        )
        call = res.phone_call
        try:
            await asyncio.sleep(seconds)
        finally:
            await self.client(
                DiscardCallRequest(
                    peer=InputPhoneCall(id=call.id, access_hash=call.access_hash),
                    duration=0,
                    reason=PhoneCallDiscardReasonHangup(),
                    connection_id=0,
                )
            )
        return call.id

    async def message(self, target, text: str) -> int:
        """Send a direct message to ``target``. Returns the message id."""
        peer = await self.resolve(target)
        msg = await self.client.send_message(peer, text)
        return msg.id

    async def whoami(self):
        """Return the logged-in userbot account (Telethon User)."""
        return await self.client.get_me()
