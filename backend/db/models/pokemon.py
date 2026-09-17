from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base


class Pokemon(Base):
    __tablename__ = "pokemon"

    id              = Column(Integer, primary_key=True)   # IF internal ID
    national_id     = Column(Integer, unique=True)        # National Pokédex (PokeAPI)
    # PokeAPI /pokemon id of an alternate form (e.g. 10019 = tornadus-therian).
    # Forms can't hold a national_id (UNIQUE, the base form owns it), so this
    # is what points them to their own sprite. NULL for base forms.
    pokeapi_form_id = Column(Integer)
    name_en         = Column(String(100), nullable=False)
    name_fr         = Column(String(100))
    generation_id   = Column(Integer, ForeignKey("generation.id"), nullable=False, index=True)
    hp              = Column(Integer, nullable=False)
    attack          = Column(Integer, nullable=False)
    defense         = Column(Integer, nullable=False)
    sp_attack       = Column(Integer, nullable=False)
    sp_defense      = Column(Integer, nullable=False)
    speed           = Column(Integer, nullable=False)
    base_experience = Column(Integer)
    is_hoenn_only   = Column(Boolean, nullable=False, default=False)
    sprite_path     = Column(Text)
    pokepedia_url   = Column(Text)

    @property
    def sprite_id(self) -> int | None:
        """PokeAPI sprite id: the alternate form's own id, else national_id.

        Deliberately never falls back to the IF id — PokeAPI would return the
        sprite of a different species (IF #431 is Glameow on PokeAPI).
        """
        return self.pokeapi_form_id or self.national_id

    generation               = relationship("Generation", back_populates="pokemon")
    types                    = relationship("PokemonType", back_populates="pokemon",
                                            cascade="all, delete-orphan")
    abilities                = relationship("PokemonAbility", back_populates="pokemon",
                                            cascade="all, delete-orphan")
    moves                    = relationship("PokemonMove", back_populates="pokemon",
                                            cascade="all, delete-orphan")
    locations                = relationship("PokemonLocation", back_populates="pokemon",
                                            cascade="all, delete-orphan")
    evolutions_from          = relationship("PokemonEvolution",
                                            foreign_keys="PokemonEvolution.pokemon_id",
                                            back_populates="pokemon",
                                            cascade="all, delete-orphan")
    evolutions_into          = relationship("PokemonEvolution",
                                            foreign_keys="PokemonEvolution.evolves_into_id",
                                            back_populates="evolves_into")
    triple_fusion_components = relationship("TripleFusionComponent",
                                            back_populates="pokemon")
    fusion_as_head           = relationship("FusionSprite", foreign_keys="FusionSprite.head_id",
                                            back_populates="head")
    fusion_as_body           = relationship("FusionSprite", foreign_keys="FusionSprite.body_id",
                                            back_populates="body")
