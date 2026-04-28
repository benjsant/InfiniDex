from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base


class TripleFusion(Base):
    __tablename__ = "triple_fusion"

    id              = Column(Integer, primary_key=True)
    name_en         = Column(String(100), nullable=False, unique=True)
    name_fr         = Column(String(100))
    hp              = Column(Integer, nullable=False)
    attack          = Column(Integer, nullable=False)
    defense         = Column(Integer, nullable=False)
    sp_attack       = Column(Integer, nullable=False)
    sp_defense      = Column(Integer, nullable=False)
    speed           = Column(Integer, nullable=False)
    evolves_from_id = Column(Integer, ForeignKey("triple_fusion.id"))
    evolution_level = Column(Integer)
    steps_to_hatch  = Column(Integer)
    sprite_path     = Column(Text)

    evolves_from = relationship("TripleFusion", remote_side="TripleFusion.id",
                                foreign_keys=[evolves_from_id],
                                back_populates="evolves_into")
    evolves_into = relationship("TripleFusion", foreign_keys=[evolves_from_id],
                                back_populates="evolves_from")
    types        = relationship("TripleFusionType", back_populates="triple_fusion",
                                cascade="all, delete-orphan")
    components   = relationship("TripleFusionComponent", back_populates="triple_fusion",
                                cascade="all, delete-orphan")
    abilities    = relationship("TripleFusionAbility", back_populates="triple_fusion",
                                cascade="all, delete-orphan")


class TripleFusionType(Base):
    __tablename__ = "triple_fusion_type"

    triple_fusion_id = Column(Integer, ForeignKey("triple_fusion.id", ondelete="CASCADE"),
                              primary_key=True)
    type_id          = Column(Integer, ForeignKey("type.id"), primary_key=True)
    slot             = Column(Integer, nullable=False)   # 1 to 4

    triple_fusion = relationship("TripleFusion", back_populates="types")
    type          = relationship("Type")


class TripleFusionComponent(Base):
    __tablename__ = "triple_fusion_component"

    triple_fusion_id = Column(Integer, ForeignKey("triple_fusion.id", ondelete="CASCADE"),
                              primary_key=True)
    pokemon_id       = Column(Integer, ForeignKey("pokemon.id"), primary_key=True)
    position         = Column(Integer, nullable=False)   # 1, 2 or 3

    triple_fusion = relationship("TripleFusion", back_populates="components")
    pokemon       = relationship("Pokemon", back_populates="triple_fusion_components")


class TripleFusionAbility(Base):
    __tablename__ = "triple_fusion_ability"

    triple_fusion_id = Column(Integer, ForeignKey("triple_fusion.id", ondelete="CASCADE"),
                              primary_key=True)
    ability_id       = Column(Integer, ForeignKey("ability.id"), primary_key=True)
    slot             = Column(Integer, nullable=False)   # 1, 2 (normal) or 3 (hidden)
    is_hidden        = Column(Boolean, nullable=False, default=False)

    triple_fusion = relationship("TripleFusion", back_populates="abilities")
    ability       = relationship("Ability")
