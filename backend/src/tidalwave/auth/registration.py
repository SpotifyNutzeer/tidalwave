from __future__ import annotations


class RegistrationDenied(Exception):
    pass


def ensure_allowed(username: str, *, mode: str, allowlist: list[str]) -> None:
    if mode == "open":
        return
    lowered = {u.lower() for u in allowlist}
    if username.lower() not in lowered:
        raise RegistrationDenied(username)
