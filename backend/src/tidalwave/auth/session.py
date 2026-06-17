from __future__ import annotations

from itsdangerous import BadSignature, URLSafeSerializer

COOKIE_NAME = "tw_session"


class SessionCodec:
    def __init__(self, secret: str) -> None:
        self._s = URLSafeSerializer(secret, salt="tidalwave-session")

    def encode(self, user_id: int) -> str:
        return self._s.dumps({"uid": user_id})

    def decode(self, token: str) -> int | None:
        try:
            data = self._s.loads(token)
        except BadSignature:
            return None
        uid = data.get("uid")
        return uid if isinstance(uid, int) else None
