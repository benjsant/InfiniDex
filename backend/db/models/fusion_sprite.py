from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base


class FusionSprite(Base):
    __tablename__ = "fusion_sprite"

    id          = Column(Integer, primary_key=True)
    head_id     = Column(Integer, ForeignKey("pokemon.id"), nullable=False)
    body_id     = Column(Integer, ForeignKey("pokemon.id"), nullable=False)
    sprite_path = Column(Text, nullable=False)
    is_custom   = Column(Boolean, nullable=False, default=False)
    is_default  = Column(Boolean, nullable=False, default=False)
    source      = Column(String(20), nullable=False, default="local")
    # local | community | auto_generated

    head     = relationship("Pokemon", foreign_keys=[head_id],
                            back_populates="fusion_as_head")
    body     = relationship("Pokemon", foreign_keys=[body_id],
                            back_populates="fusion_as_body")
    creators = relationship("FusionSpriteCreator", back_populates="fusion_sprite",
                            cascade="all, delete-orphan")


class FusionSpriteCreator(Base):
    __tablename__ = "fusion_sprite_creator"

    fusion_sprite_id = Column(Integer, ForeignKey("fusion_sprite.id", ondelete="CASCADE"),
                              primary_key=True)
    creator_id       = Column(Integer, ForeignKey("creator.id", ondelete="CASCADE"), primary_key=True)

    fusion_sprite = relationship("FusionSprite", back_populates="creators")
    creator       = relationship("Creator", back_populates="sprites")
