"""Who is asking, taken from the request, never from a tool parameter.

If a tool took ``patient_id`` as an argument, the model could be talked into asking
about someone else. So identity travels with the request: an ``Authorization``
header over HTTP, or the request ``_meta`` when the transport is in-process (tests,
local development). Tools call ``require_identity(ctx)`` and get a subject or an
``Unauthenticated`` error outcome. Nothing else is possible.

The token here is a tiny HMAC-signed demo token so the example has no dependency on
a JWT library. In production use your existing access token and verifier.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any

DEFAULT_SECRET = "dev-only-change-me"


def _secret() -> bytes:
    return os.environ.get("AGENT_TOKEN_SECRET", DEFAULT_SECRET).encode()


@dataclass(frozen=True)
class Identity:
    subject: str


class Unauthenticated(Exception):
    pass


def issue_token(subject: str, *, ttl_seconds: int = 3600, secret: bytes | None = None) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": subject, "exp": int(time.time()) + ttl_seconds}, separators=(",", ":")).encode()
    ).rstrip(b"=")
    sig = hmac.new(secret or _secret(), payload, hashlib.sha256).hexdigest()
    return f"{payload.decode()}.{sig}"


def verify_token(token: str, *, secret: bytes | None = None) -> Identity:
    try:
        payload, sig = token.split(".", 1)
    except ValueError as exc:
        raise Unauthenticated("malformed token") from exc
    expected = hmac.new(secret or _secret(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise Unauthenticated("bad signature")
    padded = payload + "=" * (-len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(padded))
    if claims.get("exp", 0) < time.time():
        raise Unauthenticated("token expired")
    if not claims.get("sub"):
        raise Unauthenticated("token has no subject")
    return Identity(subject=str(claims["sub"]))


def _bearer(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    scheme, _, token = value.partition(" ")
    return token if scheme.lower() == "bearer" and token else None


def identity_from(ctx: Any) -> Identity | None:
    """Resolve identity from an MCP request context: HTTP header first, then request meta."""
    token: str | None = None
    headers = getattr(ctx, "headers", None)
    if headers:
        token = _bearer(headers.get("authorization") or headers.get("Authorization"))
    if token is None:
        rc = getattr(ctx, "request_context", None)
        meta = getattr(rc, "meta", None) or {}
        token = _bearer(meta.get("authorization"))
    if token is None:
        return None
    return verify_token(token)


def require_identity(ctx: Any) -> Identity:
    ident = identity_from(ctx)
    if ident is None:
        raise Unauthenticated("no credentials on the request")
    return ident
