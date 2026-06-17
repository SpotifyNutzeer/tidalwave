from __future__ import annotations

import hashlib
from collections.abc import Mapping

_EXCLUDED = {"format", "callback"}


def sign(params: Mapping[str, str], *, secret: str) -> str:
    """Compute a Last.fm api_sig for the given request params."""
    parts = [f"{k}{params[k]}" for k in sorted(params) if k not in _EXCLUDED]
    raw = "".join(parts) + secret
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
