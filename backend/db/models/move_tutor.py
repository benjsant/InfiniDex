from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.db.base import Base


class MoveTutor(Base):
    """A NPC that teaches a specific move in exchange for Pokédollars, or free.

    Scope: classic tutors only (one NPC = one move).
    Out of scope: Move Relearner, Move Deleter, Egg Move Tutor (see docs),
    and Move Experts on Knot/Boon islands (see `MoveExpertMove`).
    """

    __tablename__ = "move_tutor"

    id              = Column(Integer, primary_key=True)
    move_id         = Column(Integer, ForeignKey("move.id", ondelete="CASCADE"), nullable=False)
    location_id     = Column(Integer, ForeignKey("location.id"), nullable=False)
    price           = Column(Integer)                  # NULL if free or quest reward
    currency        = Column(String(20), nullable=False)  # 'pokedollars' | 'free' | 'quest'
    npc_description = Column(Text)

    move     = relationship("Move")
    location = relationship("Location")

    __table_args__ = (
        UniqueConstraint("move_id", "location_id", name="uq_move_tutor_move_location"),
    )
