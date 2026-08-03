"""Resolve the client IP that per-IP rate limiting is keyed on.

Why this is its own module: getting it wrong silently disables the rate
limiter, and a disabled rate limiter on a public LLM endpoint is a spend
incident. The rule is narrow enough to state in one line:

    Trust exactly one header, named in config, set by a proxy that
    *overwrites* it. Otherwise use the socket peer.

``X-Forwarded-For`` does not qualify. It is a comma-separated list that any
client may send and that intermediaries append to. Reading the leftmost entry
— the common idiom, and what this project did before — takes the value most
under the attacker's control: a client that sends a fresh random
``X-Forwarded-For`` per request gets a fresh rate-limit bucket per request.

Behind Cloudflare the correct header is ``CF-Connecting-IP``, which the edge
sets and overwrites. That only holds if the origin is reachable *solely*
through the tunnel; an origin also exposed directly can be hit with a forged
header, which is why the deployment docs insist on tunnel-only ingress.
"""

from __future__ import annotations

from fastapi import Request

from app.config import get_settings

settings = get_settings()

_UNKNOWN = "0.0.0.0"


def client_ip(request: Request) -> str:
    """Best available client identifier for rate limiting.

    Falls back to the socket peer, and finally to a constant. The constant is
    deliberately a single shared bucket: if we cannot identify the caller, we
    would rather over-limit everyone than hand out unlimited quota.
    """
    header_name = settings.trusted_client_ip_header.strip().lower()

    if header_name:
        raw = request.headers.get(header_name)
        if raw:
            # Even a trusted header gets the leftmost entry taken defensively,
            # in case it is a list-shaped header behind a two-hop proxy.
            candidate = raw.split(",")[0].strip()
            if candidate:
                return candidate

    if request.client and request.client.host:
        return request.client.host

    return _UNKNOWN
