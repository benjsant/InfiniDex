from pydantic import BaseModel


class PokemonTypeOut(BaseModel):
    slot: int
    name_en: str
    name_fr: str | None

    model_config = {"from_attributes": True}


class AbilityOut(BaseModel):
    slot: int
    is_hidden: bool
    name_en: str
    name_fr: str | None

    model_config = {"from_attributes": True}


class PokemonListItem(BaseModel):
    id: int
    national_id: int | None
    name_en: str
    name_fr: str | None
    types: list[PokemonTypeOut]
    sprite_path: str | None
    is_hoenn_only: bool
    pokepedia_url: str | None

    model_config = {"from_attributes": True}


class PokemonDetail(BaseModel):
    id: int
    national_id: int | None
    name_en: str
    name_fr: str | None
    generation_id: int
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int
    base_experience: int | None
    is_hoenn_only: bool
    sprite_path: str | None
    pokepedia_url: str | None
    types: list[PokemonTypeOut]
    abilities: list[AbilityOut]

    model_config = {"from_attributes": True}
