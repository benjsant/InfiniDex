"""Prefect flow — pipeline ETL complet InfiniDex.

Orchestre les 14 étapes du pipeline en tasks Prefect séquentielles.
Chaque step est un subprocess isolé (préserve la logique existante)
avec retry et logging Prefect.

Usage manuel :
    python -m etl.flows.etl_pipeline

Déploiement Prefect planifié :
    prefect deployment run fusiondex-etl-pipeline/etl-pipeline-manual
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from prefect import flow, task
from prefect.logging import get_run_logger

from etl.pipeline import check_already_loaded

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRAPER_DIR = Path(__file__).resolve().parents[1] / "pokepedia_scraper"
PY = sys.executable

# (script_filename, cwd_override_or_None)
_STEPS: list[tuple[str, Path | None, str]] = [
    ("extract_pokedex_if.py",              None,        "1 — Extract Pokédex wiki IF"),
    ("extract_stats_pokeapi.py",           None,        "2a — Stats + FR + évolutions (PokeAPI)"),
    ("extract_pokepedia_names.py",         None,        "2b — Mapping Pokepédia"),
    ("extract_moves_if.py",                None,        "3 — Moves / TMs / tuteurs wiki IF"),
    ("enrich_moves_fr.py",                 None,        "3b — Moves FR (PokeAPI)"),
    ("extract_abilities_if.py",            None,        "4 — Abilities wiki IF"),
    ("enrich_abilities_fr.py",             None,        "4b — Abilities FR (PokeAPI)"),
    ("extract_encounters_if.py",           None,        "5 — Encounters wiki IF"),
    # Step 6 : scrapy tourne depuis pokepedia_scraper/
    ("if_movesets",                        SCRAPER_DIR, "6 — Scrape Pokepédia movesets (scrapy)"),
    ("transform_merge_movesets.py",        None,        "7 — Merge movesets"),
    ("load_db.py",                         None,        "8 — Load PostgreSQL"),
    ("fix_pokemon_types.py",               None,        "8b — Fix types (PokeAPI)"),
    ("enrich_evolution_movesets.py",       None,        "8c — Héritage moves pré-évolutions"),
    ("fix_national_ids.py",                None,        "8d — Fix national_id"),
    ("fix_stats_and_fr_names.py",          None,        "8e — Resync stats + FR"),
    ("fix_tms_from_pokeapi.py",            None,        "8f — TM gaps (PokeAPI)"),
    ("seed_type_effectiveness.py",         None,        "9 — Type effectiveness chart"),
    ("load_encounters.py",                 None,        "9b — Load locations + pokemon_location"),
    ("fix_pokemon_locations.py",           None,        "9b-bis — Fix legendary/gift/trade locations"),
    ("enrich_pokemon_fr.py",               None,        "9c — Enrich pokepedia_url"),
    ("load_items.py",                      None,        "9d — Load items"),
    ("extract_item_locations.py",          None,        "9d-bis — Item locations"),
    ("load_move_tutors.py",                None,        "9e — Move tutors"),
    ("fix_tutors_from_pokeapi.py",         None,        "9e-bis — Tutor gaps (PokeAPI)"),
    ("load_tm_locations.py",               None,        "9f — TM locations"),
    ("fix_move_experts.py",                None,        "9g — Move Experts"),
    ("extract_sprites.py",                 None,        "10 — Download sprites"),
    ("extract_triple_fusions.py",          None,        "11a — Extract triple fusions"),
    ("load_triple_fusions.py",             None,        "11b — Load triple fusions"),
    ("load_triple_fusion_type_effectiveness.py", None,  "11c — Triple fusion type effectiveness"),
    ("load_sprite_credits.py",             None,        "12 — Sprite credits"),
]


@task(retries=1, retry_delay_seconds=60)
def run_script(filename: str, cwd: Path | None, label: str) -> None:
    logger = get_run_logger()
    logger.info("▶ %s", label)

    if cwd is not None:
        # Scrapy step : `scrapy crawl <spider>`
        cmd = ["scrapy", "crawl", filename]
    else:
        cmd = [PY, str(SCRIPTS_DIR / filename)]

    result = subprocess.run(cmd, check=False, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"Step failed (code {result.returncode}): {label}")

    logger.info("✅ %s", label)


@task(name="audit-db", retries=0)
def run_audit() -> None:
    """Lance l'audit de cohérence de la base après le pipeline."""
    logger = get_run_logger()
    logger.info("▶ Audit DB — vérification cohérence post-pipeline")
    from etl.scripts.audit_db import run_audit as _audit
    _audit()


@flow(name="fusiondex-etl-pipeline", log_prints=True)
def etl_pipeline_flow(force: bool = False) -> None:
    """Pipeline ETL complet — 14 étapes + audit final.

    Args:
        force: Si True, relance même si les données sont déjà chargées.
    """
    logger = get_run_logger()

    if not force and check_already_loaded():
        logger.info("Données déjà chargées — pipeline ignoré (force=True pour relancer).")
        return

    logger.info("Démarrage du pipeline ETL InfiniDex (%d étapes).", len(_STEPS))

    for filename, cwd, label in _STEPS:
        run_script.with_options(name=label)(filename, cwd, label)

    run_audit()
    logger.info("Pipeline ETL terminé avec succès.")


if __name__ == "__main__":
    import sys as _sys
    etl_pipeline_flow(force="--force" in _sys.argv)
