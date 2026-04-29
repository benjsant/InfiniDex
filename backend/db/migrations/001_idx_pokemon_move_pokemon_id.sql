-- Migration 001: index on pokemon_move.pokemon_id
-- compute_fusion_moves queries WHERE pokemon_id IN (head_id, body_id) on ~40k rows.
-- CONCURRENTLY avoids locking the table during index creation in production.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pokemon_move_pokemon_id
    ON pokemon_move (pokemon_id);
