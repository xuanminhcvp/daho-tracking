"""Ma 2FA 6 so (TOTP, RFC 6238) tu chuoi bi mat base32 — giong Google Authenticator."""
from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time


def normalize(secret: str) -> str:
    return "".join((secret or "").split()).replace("-", "").upper()


def _key(secret: str) -> bytes:
    s = normalize(secret)
    return base64.b32decode(s + "=" * (-len(s) % 8))


def is_valid(secret: str) -> bool:
    if not normalize(secret):
        return False
    try:
        return len(_key(secret)) >= 10
    except (ValueError, TypeError):
        return False


def code(secret: str, at: float | None = None, step: int = 30) -> tuple[str, int]:
    """Tra ve (ma 6 so, so giay con hieu luc)."""
    t = time.time() if at is None else at
    counter = int(t // step)
    digest = hmac.new(_key(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    off = digest[-1] & 0x0F
    num = (struct.unpack(">I", digest[off:off + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{num:06d}", step - int(t % step)
