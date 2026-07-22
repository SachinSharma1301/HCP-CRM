from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db

router = APIRouter(prefix="/api", tags=["hcp"])


@router.get("/hcps", response_model=List[schemas.HCPOut])
def list_hcps(q: str = "", db: Session = Depends(get_db)):
    query = db.query(models.HCP)
    if q:
        query = query.filter(models.HCP.name.ilike(f"%{q}%"))
    return query.limit(20).all()


@router.get("/materials")
def list_materials(q: str = "", db: Session = Depends(get_db)):
    crud.seed_materials(db)
    return crud.search_materials(db, q)
