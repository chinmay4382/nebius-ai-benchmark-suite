"""Nebius AI Cloud authentication — fetches IAM token from instance metadata service."""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_METADATA_URL = (
    "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
)
_METADATA_HEADERS = {"Metadata-Flavor": "Google"}

_cached_token: Optional[str] = None
_token_expires_at: float = 0.0


async def get_iam_token() -> str:
    """
    Fetch IAM token from Nebius instance metadata service (when running on a Nebius VM).
    Caches the token and refreshes 60 seconds before expiry.
    Falls back to NEBIUS_API_KEY env var for local development.
    """
    global _cached_token, _token_expires_at

    # Return cached token if still valid
    if _cached_token and time.time() < _token_expires_at - 60:
        return _cached_token

    # Try metadata service first (running on Nebius VM)
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(_METADATA_URL, headers=_METADATA_HEADERS)
            if response.status_code == 200:
                data = response.json()
                _cached_token = data["access_token"]
                _token_expires_at = time.time() + data.get("expires_in", 3600)
                logger.info("IAM token fetched from metadata service (expires in %ds)", data.get("expires_in", 3600))
                return _cached_token
    except Exception as exc:
        logger.debug("Metadata service not available (not on Nebius VM?): %s", exc)

    # Fall back to API key for local dev
    api_key = os.getenv("NEBIUS_API_KEY", "")
    if api_key:
        logger.debug("Using NEBIUS_API_KEY from environment (local dev mode)")
        return api_key

    raise RuntimeError(
        "No authentication available. "
        "Either run on a Nebius VM with a service account attached, "
        "or set NEBIUS_API_KEY in your environment for local development."
    )


def get_iam_token_sync() -> str:
    """Synchronous wrapper for use outside async contexts."""
    import asyncio
    return asyncio.run(get_iam_token())


def is_on_nebius_vm() -> bool:
    """Check if running on a Nebius VM by probing the metadata service."""
    try:
        import urllib.request
        req = urllib.request.Request(_METADATA_URL, headers=_METADATA_HEADERS)
        urllib.request.urlopen(req, timeout=1)
        return True
    except Exception:
        return False
