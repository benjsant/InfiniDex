from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.db.base import Base


class PokemonLocation(Base):
    __tablename__ = "pokemon_location"

    id          = Column(Integer, primary_key=True)
    pokemon_id  = Column(Integer, ForeignKey("pokemon.id", ondelete="CASCADE"),
                         nullable=False)
    location_id = Column(Integer, ForeignKey("location.id", ondelete="RESTRICT"), nullable=False)
    method      = Column(String(20), nullable=False, default="wild")  # wild | gift | trade | static | fishing | headbutt
    notes       = Column(Text)

    __table_args__ = (
        UniqueConstraint("pokemon_id", "location_id", "method", name="uq_pokemon_location"),
    )

    pokemon  = relationship("Pokemon", back_populates="locations")
    location = relationship("Location", back_populates="pokemon_locations")
