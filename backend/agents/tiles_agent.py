"""
Tiles Agent — v0.3.

I manage the customizable quick-action tiles on the staff dashboard.
Owners control the tile list; staff and owners can read it.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import get_db, require_owner, require_can_collect

router = APIRouter(prefix="/tiles", tags=["tiles"])


@router.get("", response_model=list[schemas.TileOut])
def list_tiles(db: Session = Depends(get_db),
               _user: models.User = Depends(require_can_collect)):
    return db.query(models.Tile).filter(models.Tile.active == True) \
        .order_by(models.Tile.sort_order, models.Tile.id).all()


@router.get("/all", response_model=list[schemas.TileOut])
def list_all_tiles(db: Session = Depends(get_db),
                   _owner: models.User = Depends(require_owner)):
    """Admin view including inactive tiles."""
    return db.query(models.Tile).order_by(models.Tile.sort_order, models.Tile.id).all()


@router.post("", response_model=schemas.TileOut)
def create_tile(payload: schemas.TileCreate,
                db: Session = Depends(get_db),
                _owner: models.User = Depends(require_owner)):
    if payload.kind not in ("payment", "expense"):
        raise HTTPException(400, "kind must be 'payment' or 'expense'")
    if payload.kind == "expense" and not payload.category:
        raise HTTPException(400, "category is required for expense tiles")
    t = models.Tile(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/{tile_id}", response_model=schemas.TileOut)
def update_tile(tile_id: int, payload: schemas.TileUpdate,
                db: Session = Depends(get_db),
                _owner: models.User = Depends(require_owner)):
    t = db.query(models.Tile).filter(models.Tile.id == tile_id).first()
    if not t:
        raise HTTPException(404, "Tile not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{tile_id}")
def delete_tile(tile_id: int,
                db: Session = Depends(get_db),
                _owner: models.User = Depends(require_owner)):
    t = db.query(models.Tile).filter(models.Tile.id == tile_id).first()
    if not t:
        raise HTTPException(404, "Tile not found")
    db.delete(t)
    db.commit()
    return {"ok": True}
