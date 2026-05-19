from __future__ import annotations

from pydantic import BaseModel


class ItemLocationOut(BaseModel):
    id: int
    location_name: str
    method: str   # 'shop' | 'found' | 'wild' | 'other'
    notes: str | None

    model_config = {"from_attributes": True}


class ItemOut(BaseModel):
    """A game item (limited scope: fusion / evolution / valuable)."""
    id: int
    name_en: str
    name_fr: str | None
    category: str              # 'fusion' | 'evolution' | 'valuable'
    effect: str | None
    price_buy: int | None      # Pokédollars, NULL if not sold in shops
    price_sell: int | None     # Pokédollars, NULL if not sellable
    locations: list[ItemLocationOut] = []

    model_config = {"from_attributes": True}
