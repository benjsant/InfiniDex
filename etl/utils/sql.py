"""Generic SQL helpers for ETL load scripts."""

from __future__ import annotations


def load_id_map(
    conn,
    table: str,
    key_col: str = "name_en",
    *,
    where: str = "",
    lower: bool = True,
) -> dict:
    """Return {key_col: id} for rows of `table`.

    Args:
        conn:    psycopg2 connection.
        table:   table name.
        key_col: column used as dict key.
        where:   optional WHERE clause (without the `WHERE` keyword).
        lower:   if True, `.lower()` keys. Skipped for non-string columns.
    """
    sql = f"SELECT id, {key_col} FROM {table}"
    if where:
        sql += f" WHERE {where}"
    sql += " ORDER BY id"
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    # Deterministic: ORDER BY id + keep-first. For duplicate keys (e.g.
    # multi-form Pokémon sharing name_en — Necrozma #450/#470, Oricorio
    # #430-433…) the lowest id wins, i.e. the base/default form. Without
    # this, last-wins over an unordered SELECT made name→id resolution
    # non-deterministic and could disagree with audit_db.
    out: dict = {}
    for db_id, k in rows:
        if k is None:
            continue
        out.setdefault(k.lower() if lower else k, db_id)
    return out
