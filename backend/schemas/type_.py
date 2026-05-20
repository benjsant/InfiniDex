from __future__ import annotations

from pydantic import BaseModel


class TypeOut(BaseModel):
    id: int
    name_en: str
    name_fr: str | None
    is_triple_fusion_type: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, t) -> TypeOut | None:
        """Convert a `Type` ORM row (or None) to a `TypeOut` (or None)."""
        return cls.model_validate(t) if t is not None else None
