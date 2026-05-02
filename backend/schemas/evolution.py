from pydantic import BaseModel


class EvolutionOut(BaseModel):
    id: int
    pokemon_id: int
    pokemon_name_en: str | None = None
    pokemon_name_fr: str | None = None
    pokemon_national_id: int | None = None
    evolves_into_id: int
    evolves_into_name_en: str
    evolves_into_name_fr: str | None
    evolves_into_national_id: int | None = None
    trigger_type: str           # level_up | use_item | trade | friendship | other
    min_level: int | None
    item_name_en: str | None
    item_name_fr: str | None
    if_override: bool
    if_notes: str | None

    model_config = {"from_attributes": True}
