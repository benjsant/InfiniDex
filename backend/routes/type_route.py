"""API routes for types."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.type_ import TypeOut
from backend.services.type_service import (
    find_type_by_name,
    get_type_by_id,
    list_types,
)

router = APIRouter(prefix="/types", tags=["Types"])


@router.get("/", response_model=list[TypeOut])
def get_types(db: Session = Depends(get_db)):
    """List all 27 IF types (18 standard + 9 triple-fusion)."""
    return list_types(db)


@router.get("/by-name/{name}", response_model=TypeOut)
def get_type_by_name(name: str = Path(..., min_length=1, max_length=50), db: Session = Depends(get_db)):
    """Find a type by EN or FR name (accent-insensitive, prefix match)."""
    t = find_type_by_name(db, name)
    if not t:
        raise HTTPException(status_code=404, detail=f"Type '{name}' not found")
    return t


@router.get("/{type_id}", response_model=TypeOut)
def get_type(type_id: int, db: Session = Depends(get_db)):
    """Type by ID."""
    t = get_type_by_id(db, type_id)
    if not t:
        raise HTTPException(status_code=404, detail="Type not found")
    return t
