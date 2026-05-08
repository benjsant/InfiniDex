from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base


class Move(Base):
    __tablename__ = "move"

    id             = Column(Integer, primary_key=True)
    name_en        = Column(String(100), nullable=False, unique=True)
    name_fr        = Column(String(100))
    type_id        = Column(Integer, ForeignKey("type.id"), nullable=False, index=True)
    category       = Column(String(10), nullable=False)   # Physical | Special | Status
    power          = Column(Integer)                       # NULL for Status moves
    accuracy       = Column(Integer)                       # NULL if accuracy is infinite
    pp             = Column(Integer, nullable=False)
    description_en = Column(Text)
    description_fr = Column(Text)
    source         = Column(String(20), nullable=False, default="base")

    type           = relationship("Type", back_populates="moves")
    tm             = relationship("TM", back_populates="move", uselist=False)
    pokemon_moves  = relationship("PokemonMove", back_populates="move")
