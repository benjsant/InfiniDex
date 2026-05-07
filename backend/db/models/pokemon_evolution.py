from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.db.base import Base


class PokemonEvolution(Base):
    __tablename__ = "pokemon_evolution"

    id              = Column(Integer, primary_key=True)
    pokemon_id      = Column(Integer, ForeignKey("pokemon.id", ondelete="CASCADE"), nullable=False)
    evolves_into_id = Column(Integer, ForeignKey("pokemon.id", ondelete="CASCADE"), nullable=False)
    trigger_type    = Column(String(20), nullable=False)
    # level_up | use_item | trade | friendship | other
    min_level       = Column(Integer)
    item_name_en    = Column(String(100))
    item_name_fr    = Column(String(100))
    if_override     = Column(Boolean, nullable=False, default=False)
    if_notes        = Column(Text)   # description lisible de la condition IF

    __table_args__ = (
        UniqueConstraint("pokemon_id", "evolves_into_id", "trigger_type", "item_name_en",
                         name="uq_pokemon_evolution"),
    )

    pokemon      = relationship("Pokemon", foreign_keys=[pokemon_id],
                                back_populates="evolutions_from")
    evolves_into = relationship("Pokemon", foreign_keys=[evolves_into_id],
                                back_populates="evolutions_into")
