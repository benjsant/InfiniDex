"""
ETL Step 9 — Download & extract fusion sprites from infinitefusion.net.

Optimizations:
  - Filter by real IF IDs (data/pokedex_if.json) → ignore out-of-game sprites
  - By default: main sprites only (alt="")
  - Option --alts: include community variants (a, b, c...)
  - A single request per spritesheet → crop all body_ids in one pass

Keeping sprites in sync with REDRAWS (not just additions):
  Artists redraw sprites under the same filename, so CUSTOM_SPRITES doesn't
  change and "skip if the file exists" kept stale art forever — while
  load_sprite_credits.py already credited the NEW artist on the OLD image.
  Each sheet's ETag is stored in data/spritesheet_etags.json (local state,
  tied to data/sprites/). Every run sends a conditional GET per sheet:
    304 → unchanged, nothing downloaded;
    200 → sheet changed: re-crop every sprite, rewrite only those whose
          pixels differ.
  A sheet with no stored ETag (first run) is downloaded once and verified.

Sprite grid layout (CustomSpriteExtracter.rb):
  Size: 96×96 px | Columns: 20
  Position: col = body_id % 20 / row = body_id // 20

URLs (pif-downloadables/Settings.rb):
  Spritesheets : https://infinitefusion.net/customsprites/spritesheets/spritesheets_custom/{head}/{head}{alt}.png
  Credits      : https://infinitefusion.net/customsprites/Sprite_Credits.csv
  Sprite list  : https://raw.githubusercontent.com/infinitefusion/pif-downloadables/master/CUSTOM_SPRITES
"""

from __future__ import annotations

import io
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests
from PIL import Image

from etl.utils.http import USER_AGENT
from etl.utils.io import load_json
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR       = Path(__file__).resolve().parents[2] / "data"
SPRITES_DIR    = DATA_DIR / "sprites"
CREDITS_OUT    = DATA_DIR / "sprite_credits.csv"
# Committed baseline: how many entries CUSTOM_SPRITES held at the last
# successful extraction. check_sources.py compares it to the live list so the
# weekly CI watch can say "a new spritepack landed — re-run the ETL" without
# needing any persistent state of its own.
SPRITES_BASELINE = DATA_DIR / "sprites_baseline.txt"
# Local (gitignored) ETag per spritesheet — see "Keeping sprites in sync".
SHEET_ETAGS    = DATA_DIR / "spritesheet_etags.json"
POKEDEX_IF     = DATA_DIR / "pokedex_if.json"

# ── URLs ──────────────────────────────────────────────────────────────────────
CUSTOM_SPRITES_URL   = "https://raw.githubusercontent.com/infinitefusion/pif-downloadables/master/CUSTOM_SPRITES"
SPRITE_CREDITS_URL   = "https://infinitefusion.net/customsprites/Sprite_Credits.csv"
SPRITESHEET_BASE_URL = "https://infinitefusion.net/customsprites/spritesheets/spritesheets_custom"

# ── Constants ─────────────────────────────────────────────────────────────────
SPRITE_SIZE    = 96
GRID_COLS      = 20
DOWNLOAD_DELAY = 2.0    # seconds after a full spritesheet download (respectful)
REVALIDATE_DELAY = 0.1  # after a 304 (no body transferred)
ETAGS_SAVE_EVERY = 25   # sheets — an interrupted first run keeps its progress

SPRITE_RE = re.compile(r"^(\d+)\.(\d+)([a-z]*)\.png$")

HEADERS = {"User-Agent": USER_AGENT}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_if_ids() -> set[int]:
    """
    Load the IF IDs from data/pokedex_if.json.
    If the file doesn't exist yet (ETL run outside the pipeline), return an
    empty set which disables the filter.
    """
    if not POKEDEX_IF.exists():
        LOGGER.warning(
            "pokedex_if.json not found — no ID filter applied (run extract_pokedex_if.py first)"
        )
        return set()
    entries = load_json(POKEDEX_IF)
    ids = {e["if_id"] for e in entries}
    LOGGER.info("Loaded %d IF Pokémon IDs from pokedex_if.json", len(ids))
    return ids


def fetch_text(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_sheet(url: str, etag: str | None) -> tuple[str, bytes | None, str | None]:
    """Conditional GET of a spritesheet.

    Returns ``(status, content, etag)`` with status one of:
      "not_modified" — 304, the stored ETag is still current (no body);
      "modified"     — 200, content + the new ETag;
      "missing"      — 404 or repeated failure.
    Retries with backoff on 429/503/network errors.
    """
    headers = dict(HEADERS)
    if etag:
        headers["If-None-Match"] = etag
    for attempt in range(1, 4):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 304:
                return "not_modified", None, etag
            if resp.status_code == 200:
                return "modified", resp.content, resp.headers.get("ETag")
            if resp.status_code in (429, 503) and attempt < 3:
                wait = 5 * 2 ** (attempt - 1)
                LOGGER.warning("HTTP %s — %s — backing off %ss", resp.status_code, url, wait)
                time.sleep(wait)
                continue
            LOGGER.warning("HTTP %s — %s", resp.status_code, url)
            return "missing", None, None
        except requests.RequestException as e:
            if attempt < 3:
                wait = 5 * 2 ** (attempt - 1)
                LOGGER.warning("Request failed %s — %s — retry in %ss", url, e, wait)
                time.sleep(wait)
                continue
            LOGGER.warning("Request failed %s — %s", url, e)
    return "missing", None, None


def write_sheet_sprites(
    sheet: Image.Image, head_id: int, alt: str, body_ids: list[int], sprites_dir: Path,
) -> tuple[int, int, int, int]:
    """Crop every body_id from a sheet; write only new or changed sprites.

    Returns ``(created, refreshed, unchanged, failed)``. Pixels are compared
    (RGBA), not file bytes, so re-encoding differences never count as a change.
    """
    created = refreshed = unchanged = failed = 0
    for body_id in body_ids:
        out_path = sprites_dir / f"{head_id}.{body_id}{alt}.png"
        try:
            new = crop_sprite(sheet, body_id).convert("RGBA")
            if out_path.exists():
                with Image.open(out_path) as old:
                    if old.convert("RGBA").tobytes() == new.tobytes():
                        unchanged += 1
                        continue
                new.save(out_path, format="PNG")
                refreshed += 1
            else:
                new.save(out_path, format="PNG")
                created += 1
        except Exception as e:
            LOGGER.warning("Crop failed head=%d body=%d: %s", head_id, body_id, e)
            failed += 1
    return created, refreshed, unchanged, failed


def load_etags(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = load_json(path)
        return data if isinstance(data, dict) else {}
    except Exception:
        LOGGER.warning("%s unreadable — every sheet will be re-verified", path.name)
        return {}


def save_etags(path: Path, etags: dict[str, str]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(etags, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def crop_sprite(sheet: Image.Image, body_id: int) -> Image.Image:
    col = body_id % GRID_COLS
    row = body_id // GRID_COLS
    x   = col * SPRITE_SIZE
    y   = row * SPRITE_SIZE
    return sheet.crop((x, y, x + SPRITE_SIZE, y + SPRITE_SIZE))


def parse_and_filter(
    raw: str,
    if_ids: set[int],
    include_alts: bool,
) -> dict[tuple[int, str], list[int]]:
    """
    Parse CUSTOM_SPRITES and return {(head_id, alt): [body_id, ...]}
    applying two filters:
      1. head_id AND body_id must be in if_ids (if if_ids is non-empty)
      2. alts (a, b, c...) are excluded unless include_alts=True
    """
    groups: dict[tuple[int, str], list[int]] = defaultdict(list)
    total = skipped_id = skipped_alt = 0

    for line in raw.splitlines():
        line = line.strip()
        m    = SPRITE_RE.match(line)
        if not m:
            continue

        total   += 1
        head_id  = int(m.group(1))
        body_id  = int(m.group(2))
        alt      = m.group(3)

        # Filter 1 — IF IDs only
        if if_ids and (head_id not in if_ids or body_id not in if_ids):
            skipped_id += 1
            continue

        # Filter 2 — optional alts
        if alt and not include_alts:
            skipped_alt += 1
            continue

        groups[(head_id, alt)].append(body_id)

    kept = sum(len(v) for v in groups.values())
    LOGGER.info(
        "CUSTOM_SPRITES: %d total → kept=%d / filtered out-of-IF=%d / alts excluded=%d",
        total, kept, skipped_id, skipped_alt,
    )
    return groups


# ── Core ──────────────────────────────────────────────────────────────────────

def download_credits() -> None:
    LOGGER.info("Downloading Sprite_Credits.csv...")
    raw = fetch_text(SPRITE_CREDITS_URL)
    CREDITS_OUT.write_text(raw, encoding="utf-8")
    LOGGER.info("Credits → %s", CREDITS_OUT)


def count_sprite_entries(raw_list: str) -> int:
    """Number of .png entries in a CUSTOM_SPRITES listing (unfiltered)."""
    return sum(1 for line in raw_list.splitlines() if line.strip().endswith(".png"))


def extract_sprites(force: bool, include_alts: bool) -> None:
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)

    if_ids   = load_if_ids()
    raw_list = fetch_text(CUSTOM_SPRITES_URL)
    groups   = parse_and_filter(raw_list, if_ids, include_alts)

    n_sheets  = len(groups)
    n_sprites = sum(len(v) for v in groups.values())
    LOGGER.info("To download: %d spritesheets / %d sprites", n_sheets, n_sprites)

    etags = {} if force else load_etags(SHEET_ETAGS)
    created = refreshed = unchanged = revalidated = failed = 0
    sheets_changed = 0

    for idx, ((head_id, alt), body_ids) in enumerate(sorted(groups.items()), 1):
        key       = f"{head_id}{alt}"
        sheet_url = f"{SPRITESHEET_BASE_URL}/{head_id}/{head_id}{alt}.png"

        # Revalidate only when every sprite is on disk AND we know the ETag:
        # a missing sprite, or a sheet never verified, needs the content.
        all_present = all((SPRITES_DIR / f"{head_id}.{b}{alt}.png").exists() for b in body_ids)
        known_etag  = etags.get(key) if all_present else None

        status, content, etag = fetch_sheet(sheet_url, known_etag)

        if status == "not_modified":
            revalidated += len(body_ids)
            time.sleep(REVALIDATE_DELAY)
            continue

        if status == "missing" or content is None:
            LOGGER.warning("[%d/%d] Missing spritesheet head=%d alt='%s'", idx, n_sheets, head_id, alt)
            failed += len(body_ids)
            continue

        try:
            sheet = Image.open(io.BytesIO(content)).convert("RGBA")
        except Exception as e:
            LOGGER.warning("Could not open spritesheet %s: %s", sheet_url, e)
            failed += len(body_ids)
            continue

        c, r, u, f = write_sheet_sprites(sheet, head_id, alt, body_ids, SPRITES_DIR)
        created, refreshed, unchanged, failed = created + c, refreshed + r, unchanged + u, failed + f
        if f == 0 and etag:
            etags[key] = etag           # only a fully written sheet is "in sync"
        if c or r:
            sheets_changed += 1
            LOGGER.info("[%d/%d] head=%d alt='%s' → %d new, %d redrawn", idx, n_sheets, head_id, alt, c, r)

        if idx % ETAGS_SAVE_EVERY == 0:
            save_etags(SHEET_ETAGS, etags)
        time.sleep(DOWNLOAD_DELAY)

    save_etags(SHEET_ETAGS, etags)
    LOGGER.info(
        "Done — new=%d / redrawn=%d / verified-identical=%d / unchanged-304=%d / failed=%d "
        "(%d sheet(s) changed, %d ETags stored)",
        created, refreshed, unchanged, revalidated, failed, sheets_changed, len(etags),
    )

    # Record the size of the list we just consumed. Only on a clean run: a
    # partial extraction must not claim we are in sync with upstream.
    if failed == 0:
        count = count_sprite_entries(raw_list)
        SPRITES_BASELINE.write_text(f"{count}\n", encoding="utf-8")
        LOGGER.info("Baseline CUSTOM_SPRITES → %d (%s)", count, SPRITES_BASELINE.name)
    else:
        LOGGER.warning(
            "%d spritesheet(s) failed — baseline left untouched (still out of sync)",
            failed,
        )


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    force        = "--force" in sys.argv
    include_alts = "--alts"  in sys.argv
    download_credits()
    extract_sprites(force=force, include_alts=include_alts)


if __name__ == "__main__":
    main()
