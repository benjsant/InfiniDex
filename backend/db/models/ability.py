from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base


class Ability(Base):
    __tablename__ = "ability"

    id             = Column(Integer, primary_key=True)
    name_en        = Column(String(100), nullable=False, unique=True)
    name_fr        = Column(String(100))
    description_en = Column(Text)
    description_fr = Column(Text)

    pokemon_abilities = relationship("PokemonAbility", back_populates="ability")
