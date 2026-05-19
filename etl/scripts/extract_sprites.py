"""
ETL Step 9 — Download & extract fusion sprites from infinitefusion.net.

Optimizations:
  - Filter by real IF IDs (data/pokedex_if.json) → ignore out-of-game sprites
  - By default: main sprites only (alt="")
  - Option --alts: include community variants (a, b, c...)
  - Idempotent: skip sprites already extracted (unless --force)
  - A single request per spritesheet → crop all body_ids in one pass

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
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests
from PIL import Image

from etl.utils.io import load_json
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR       = Path(__file__).resolve().parents[2] / "data"
SPRITES_DIR    = DATA_DIR / "sprites"
CREDITS_OUT    = DATA_DIR / "sprite_credits.csv"
POKEDEX_IF     = DATA_DIR / "pokedex_if.json"

# ── URLs ──────────────────────────────────────────────────────────────────────
CUSTOM_SPRITES_URL   = "https://raw.githubusercontent.com/infinitefusion/pif-downloadables/master/CUSTOM_SPRITES"
SPRITE_CREDITS_URL   = "https://infinitefusion.net/customsprites/Sprite_Credits.csv"
SPRITESHEET_BASE_URL = "https://infinitefusion.net/customsprites/spritesheets/spritesheets_custom"

# ── Constants ─────────────────────────────────────────────────────────────────
SPRITE_SIZE    = 96
GRID_COLS      = 20
DOWNLOAD_DELAY = 2.0    # seconds between two spritesheets (respectful)

SPRITE_RE = re.compile(r"^(\d+)\.(\d+)([a-z]*)\.png$")


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
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_bytes(url: str) -> bytes | None:
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.content
        LOGGER.warning("HTTP %s — %s", resp.status_code, url)
        return None
    except requests.RequestException as e:
        LOGGER.warning("Request failed %s — %s", url, e)
        return None


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


def extract_sprites(force: bool, include_alts: bool) -> None:
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)

    if_ids   = load_if_ids()
    raw_list = fetch_text(CUSTOM_SPRITES_URL)
    groups   = parse_and_filter(raw_list, if_ids, include_alts)

    n_sheets  = len(groups)
    n_sprites = sum(len(v) for v in groups.values())
    LOGGER.info("To download: %d spritesheets / %d sprites", n_sheets, n_sprites)

    extracted = skipped = failed = 0

    for idx, ((head_id, alt), body_ids) in enumerate(sorted(groups.items()), 1):

        # Skip if all sprites already exist
        if not force:
            missing = [
                b for b in body_ids
                if not (SPRITES_DIR / f"{head_id}.{b}{alt}.png").exists()
            ]
            if not missing:
                skipped += len(body_ids)
                continue
            body_ids = missing

        # Download the spritesheet only once
        sheet_url  = f"{SPRITESHEET_BASE_URL}/{head_id}/{head_id}{alt}.png"
        sheet_data = fetch_bytes(sheet_url)

        if sheet_data is None:
            LOGGER.warning("[%d/%d] Missing spritesheet head=%d alt='%s'", idx, n_sheets, head_id, alt)
            failed += len(body_ids)
            continue

        try:
            sheet = Image.open(io.BytesIO(sheet_data)).convert("RGBA")
        except Exception as e:
            LOGGER.warning("Could not open spritesheet %s: %s", sheet_url, e)
            failed += len(body_ids)
            continue

        # Crop all body_ids in a single pass
        for body_id in body_ids:
            out_path = SPRITES_DIR / f"{head_id}.{body_id}{alt}.png"
            try:
                crop_sprite(sheet, body_id).save(out_path, format="PNG")
                extracted += 1
            except Exception as e:
                LOGGER.warning("Crop failed head=%d body=%d: %s", head_id, body_id, e)
                failed += 1

        LOGGER.info("[%d/%d] head=%d alt='%s' → %d sprites", idx, n_sheets, head_id, alt, len(body_ids))
        time.sleep(DOWNLOAD_DELAY)

    LOGGER.info(
        "Done — extracted=%d / skipped=%d / failed=%d",
        extracted, skipped, failed,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    force        = "--force" in sys.argv
    include_alts = "--alts"  in sys.argv
    download_credits()
    extract_sprites(force=force, include_alts=include_alts)


if __name__ == "__main__":
    main()
