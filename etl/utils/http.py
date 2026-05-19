"""HTTP helpers with retry logic for ETL scripts."""

from __future__ import annotations

import logging
import time

import requests

LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2          # base; exponential backoff = RETRY_DELAY * 2**(attempt-1)
REQUEST_TIMEOUT = 10

# Identifying User-Agent — be a good web citizen so the wiki/API operators can
# identify and contact this client (matches the fix_*_from_pokeapi scripts).
USER_AGENT = "InfiniDexETL/1.0 (+https://github.com/benjsant/InfiniDex-IA; educational)"
HEADERS = {"User-Agent": USER_AGENT}


def get_json(url: str, params: dict | None = None) -> dict | None:
    """GET a JSON endpoint with retry + exponential backoff (429/503-aware)."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT
            )
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 503):
                ra = resp.headers.get("Retry-After")
                wait = (
                    int(ra) if (ra and ra.isdigit())
                    else RETRY_DELAY * 2 ** (attempt - 1)
                )
                LOGGER.warning(
                    "HTTP %s — %s (attempt %s) — backing off %ss",
                    resp.status_code, url, attempt, wait,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                continue
            LOGGER.warning("HTTP %s — %s (attempt %s)", resp.status_code, url, attempt)
        except requests.RequestException as exc:
            LOGGER.warning("Request failed: %s (attempt %s): %s", url, attempt, exc)

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY * 2 ** (attempt - 1))

    return None
