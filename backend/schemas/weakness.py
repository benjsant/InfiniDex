from pydantic import BaseModel


class WeaknessOut(BaseModel):
    """Damage multiplier for one attacking type against a Pokémon."""
    attacking_type_id: int
    attacking_type_name_en: str
    attacking_type_name_fr: str | None
    multiplier: float

    model_config = {"from_attributes": True}
