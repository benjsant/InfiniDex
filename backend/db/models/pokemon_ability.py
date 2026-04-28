from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from backend.db.base import Base


class PokemonAbility(Base):
    __tablename__ = "pokemon_ability"

    pokemon_id  = Column(Integer, ForeignKey("pokemon.id", ondelete="CASCADE"),
                         primary_key=True)
    ability_id  = Column(Integer, ForeignKey("ability.id"), nullable=False)
    slot        = Column(Integer, primary_key=True)   # 1, 2 (normal) or 3 (hidden)
    is_hidden   = Column(Boolean, nullable=False, default=False)
    if_swapped  = Column(Boolean, nullable=False, default=False)  # slots 1/2 swapped in IF
    if_override = Column(Boolean, nullable=False, default=False)  # ability replaced in IF

    pokemon = relationship("Pokemon", back_populates="abilities")
    ability = relationship("Ability", back_populates="pokemon_abilities")
