"""PokeAPI helpers shared by enrichment scripts.

Two pieces are factored out here:

1. `fetch_fr_translation(url, version_prio)` — hits a PokeAPI resource URL
   (move, ability, pokemon-species…), extracts the French name from `names`
   and the most recent FR flavor text matching `version_prio`. Returns
   `(name_fr, desc_fr)` — either field may be None on failure.

2. `enrich_items_parallel(...)` — the threaded enrichment loop with
   periodic checkpointing, shared by `enrich_moves_fr.py` and
   `enrich_abilities_fr.py`. Handles progress logging and the `not_found`
   list so individual scripts only need to supply a single-item worker.

Neither helper knows anything about the ETL data shape beyond
`item["name_en"]` for failure reporting.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from logging import Logger
from typing import Callable, Iterable, Sequence

import requests

from etl.utils.http import USER_AGENT

_HEADERS = {"User-Agent": USER_AGENT}


def fetch_fr_translation(
    url: str,
    version_prio: Sequence[str],
    *,
    timeout: int = 10,
    logger: Logger | None = None,
) -> tuple[str | None, str | None]:
    """Fetch French (name, description) from a PokeAPI resource URL.

    `version_prio` is an ordered list of `version_group` slugs — the first
    entry with a French flavor text wins. Newlines and non-breaking spaces
    in the description are normalized to regular spaces.

    Retries with exponential backoff on 429/503 (honouring Retry-After).
    """
    data = None
    for attempt in range(1, 4):
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                break
            if resp.status_code in (429, 503):
                ra = resp.headers.get("Retry-After")
                wait = int(ra) if (ra and ra.isdigit()) else 2 ** attempt
                if logger is not None:
                    logger.warning(
                        "PokeAPI %s %s — backing off %ss", resp.status_code, url, wait
                    )
                time.sleep(wait)
                continue
            return None, None
        except Exception as exc:
            if logger is not None:
                logger.debug("PokeAPI error %s: %s", url, exc)
            return None, None
    if data is None:
        return None, None

    name_fr = next(
        (n["name"] for n in data.get("names", []) if n["language"]["name"] == "fr"),
        None,
    )

    desc_fr: str | None = None
    for vg in version_prio:
        match = next(
            (
                e["flavor_text"]
                for e in data.get("flavor_text_entries", [])
                if e["language"]["name"] == "fr" and e["version_group"]["name"] == vg
            ),
            None,
        )
        if match:
            desc_fr = match.replace("\n", " ").replace("\xa0", " ")
            break

    return name_fr, desc_fr


def enrich_items_parallel(
    items: Iterable[dict],
    worker: Callable[[dict], tuple[dict, str | None, str | None]],
    *,
    save: Callable[[], None],
    logger: Logger,
    save_every: int = 100,
    max_workers: int = 2,
    label: str = "items",
) -> tuple[int, list[str]]:
    """Run `worker` over `items` in a thread pool with periodic saves.

    `worker(item)` must return `(item, name_fr, desc_fr)`. When `name_fr`
    is non-None it is written onto the item as `name_fr`/`description_fr`
    (the scripts mutate the underlying list in place, so callers keep
    ownership of the data structure).

    Returns `(found_count, not_found_names)`.
    """
    items_list = list(items)
    total = len(items_list)
    found = 0
    not_found: list[str] = []
    lock = threading.Lock()
    done = 0

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(worker, it): it for it in items_list}
        for future in as_completed(futures):
            item, name_fr, desc_fr = future.result()
            with lock:
                done += 1
                if name_fr:
                    item["name_fr"] = name_fr
                    item["description_fr"] = desc_fr
                    found += 1
                else:
                    not_found.append(item.get("name_en", "?"))
                if done % save_every == 0:
                    save()
                    logger.info(
                        "[%d/%d] %s — %d found, %d not found",
                        done, total, label, found, len(not_found),
                    )

    save()
    return found, not_found


def sleep_between_requests(delay: float) -> None:
    """Tiny wrapper so callers don't need to import `time` just for this."""
    if delay > 0:
        time.sleep(delay)
