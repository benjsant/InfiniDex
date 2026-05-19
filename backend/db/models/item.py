from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base


class Item(Base):
    """Game item (scope restreint : fusion / evolution / valuable).

    Source : https://infinitefusion.fandom.com/wiki/List_of_Items
    """

    __tablename__ = "item"

    id         = Column(Integer, primary_key=True)
    name_en    = Column(String(100), nullable=False, unique=True)
    name_fr    = Column(String(100))
    category   = Column(String(20), nullable=False)  # 'fusion' | 'evolution' | 'valuable'
    effect     = Column(Text)
    price_buy  = Column(Integer)
    price_sell = Column(Integer)

    locations  = relationship("ItemLocation", back_populates="item", order_by="ItemLocation.method, ItemLocation.location_name")


class ItemLocation(Base):
    """Where an item can be obtained in the game.

    Source : https://infinitefusion.fandom.com/wiki/List_of_Items
    """

    __tablename__ = "item_location"

    id            = Column(Integer, primary_key=True)
    item_id       = Column(Integer, ForeignKey("item.id", ondelete="CASCADE"), nullable=False)
    location_name = Column(String(200), nullable=False)
    method        = Column(String(20), nullable=False)  # 'shop' | 'found' | 'wild' | 'other'
    notes         = Column(Text)

    item = relationship("Item", back_populates="locations")
