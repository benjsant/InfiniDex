from __future__ import annotations

from pydantic import BaseModel

from backend.schemas.type_ import TypeOut


class FusionMoveOut(BaseModel):
    """Move learnable by a fusion — includes which parent teaches it."""
    move_id: int
    name_en: str
    name_fr: str | None
    category: str
    power: int | None
    accuracy: int | None
    pp: int
    type: TypeOut
    method: str
    level: int | None
    source: str
    origin: str  # 'head' | 'body' | 'both'

    model_config = {"from_attributes": True}


class FusionAbilityOut(BaseModel):
    """Ability available to a fusion, labelled by origin."""
    ability_id: int
    name_en: str
    name_fr: str | None
    is_hidden: bool
    origin: str  # 'head' | 'body'

    model_config = {"from_attributes": True}


class FusionResult(BaseModel):
    head_id: int
    body_id: int
    head_name_en: str
    head_name_fr: str | None
    body_name_en: str
    body_name_fr: str | None
    # Computed stats
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int
    # Types: head gives type1, body gives type2
    type1: TypeOut | None
    type2: TypeOut | None
    # Sprite path pattern: "{head_id}.{body_id}.png"
    sprite_path: str


class FusionExpertMoveOut(BaseModel):
    """Move teachable to a fusion by a Move Expert (Knot / Boon Island)."""
    move_id: int
    name_en: str
    name_fr: str | None
    category: str
    power: int | None
    accuracy: int | None
    pp: int
    type: TypeOut
    locations: list[str]                       # ['knot_island'] / ['boon_island'] / both
    prices_heart_scales: dict[str, int]        # map location → price in Heart Scales

    model_config = {"from_attributes": True}


class FusionInvolvingOut(BaseModel):
    head_id: int
    body_id: int
    role: str  # 'head' | 'body' — role of the queried Pokémon
    partner_id: int
    partner_name_en: str | None
    partner_name_fr: str | None

    model_config = {"from_attributes": True}
