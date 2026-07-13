"""HTTP helpers with retry logic and a shared on-disk cache for ETL scripts.

The cache is the main performance lever of the pipeline: the same PokeAPI
resources are needed by several steps (2a, 8e, 8e-bis, 8e-quater, 14, ...) and
a full rebuild used to re-fetch each of them every time. Responses are stored
as JSON under ``data/cache/http/`` (mounted, so they survive container runs)
with a TTL. This is also what PokeAPI's fair-use policy asks of clients:
cache locally, avoid hammering.

Tuning via env:
    ETL_HTTP_CACHE_TTL_HOURS  — default 24; 0 disables the cache entirely.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable

import requests

LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2          # base; exponential backoff = RETRY_DELAY * 2**(attempt-1)
REQUEST_TIMEOUT = 10

# Identifying User-Agent — be a good web citizen so the wiki/API operators can
# identify and contact this client (matches the fix_*_from_pokeapi scripts).
USER_AGENT = "InfiniDexETL/1.0 (+https://github.com/benjsant/InfiniDex; educational)"
HEADERS = {"User-Agent": USER_AGENT}

CACHE_DIR = Path("data/cache/http")
CACHE_TTL_HOURS = float(os.getenv("ETL_HTTP_CACHE_TTL_HOURS", "24"))

# Default worker count for prefetch_json. PokeAPI is a CDN-backed static API;
# a handful of parallel requests is well within polite use.
PREFETCH_WORKERS = 6


def _cache_path(url: str, params: dict | None) -> Path:
    key = hashlib.sha256(
        f"{url}?{json.dumps(params or {}, sort_keys=True)}".encode()
    ).hexdigest()
    return CACHE_DIR / key[:2] / f"{key}.json"


def _cache_read(path: Path) -> dict | None:
    if CACHE_TTL_HOURS <= 0 or not path.exists():
        return None
    if (time.time() - path.stat().st_mtime) / 3600 >= CACHE_TTL_HOURS:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None   # corrupt/partial entry → refetch


def _cache_write(path: Path, data: dict) -> None:
    if CACHE_TTL_HOURS <= 0:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)   # atomic — safe under prefetch concurrency
    except OSError as exc:
        LOGGER.debug("Cache write failed for %s: %s", path, exc)


def get_json(url: str, params: dict | None = None, *, cache: bool = True) -> dict | None:
    """GET a JSON endpoint with retry + exponential backoff (429/503-aware).

    Successful responses are cached on disk (TTL ``ETL_HTTP_CACHE_TTL_HOURS``,
    default 24h). Pass ``cache=False`` to force a live fetch.
    """
    path = _cache_path(url, params)
    if cache:
        cached = _cache_read(path)
        if cached is not None:
            return cached

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT
            )
            if resp.status_code == 200:
                data = resp.json()
                if cache:
                    _cache_write(path, data)
                return data
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


def prefetch_json(urls: Iterable[str], workers: int = PREFETCH_WORKERS) -> None:
    """Warm the disk cache for a batch of URLs with a small thread pool.

    Cache hits cost nothing; misses are fetched concurrently. Callers keep
    their existing sequential loops (which then read from the cache), so the
    parallelism stays contained here.
    """
    urls = list(dict.fromkeys(urls))
    if not urls:
        return
    LOGGER.info("Prefetching %d URLs (%d workers)...", len(urls), workers)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(get_json, urls))
