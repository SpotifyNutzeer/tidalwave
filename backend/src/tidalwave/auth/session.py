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


from fastapi import Depends, HTTPException, Request  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from tidalwave.deps import get_session, get_settings  # noqa: E402
from tidalwave.models.db import User  # noqa: E402


async def current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings=Depends(get_settings),
) -> User:
    token = request.cookies.get(COOKIE_NAME)
    uid = SessionCodec(settings.session_secret).decode(token) if token else None
    user = await session.get(User, uid) if uid is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
