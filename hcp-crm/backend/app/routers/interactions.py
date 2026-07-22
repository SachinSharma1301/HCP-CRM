from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.agent.tools import suggest_followups

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


def _serialize(interaction) -> schemas.InteractionOut:
    return schemas.InteractionOut(
        id=interaction.id,
        hcp_id=interaction.hcp_id,
        hcp_name=interaction.hcp.name,
        interaction_type=interaction.interaction_type,
        date=interaction.date,
        time=interaction.time,
        attendees=interaction.attendees,
        topics_discussed=interaction.topics_discussed,
        materials_shared=interaction.materials_shared or [],
        samples_distributed=interaction.samples_distributed or [],
        sentiment=interaction.sentiment.value
        if hasattr(interaction.sentiment, "value")
        else interaction.sentiment,
        outcomes=interaction.outcomes,
        follow_up_actions=interaction.follow_up_actions,
        ai_suggested_followups=interaction.ai_suggested_followups or [],
        ai_summary=interaction.ai_summary,
    )


@router.post("", response_model=schemas.InteractionOut)
def create_interaction(payload: schemas.InteractionCreate, db: Session = Depends(get_db)):
    """Create an interaction from the structured form. This does NOT require
    the LLM (the form already gives structured fields), but we still call the
    suggest_followups tool afterwards so the UI can show AI-suggested next
    steps, matching the mockup."""
    interaction = crud.create_interaction(db, payload.hcp_name, payload.model_dump())
    try:
        suggest_followups.invoke({"interaction_id": interaction.id})
        db.refresh(interaction)
    except Exception:
        pass
    return _serialize(interaction)


@router.patch("/{interaction_id}", response_model=schemas.InteractionOut)
def edit_interaction_endpoint(
    interaction_id: int, payload: schemas.InteractionUpdate, db: Session = Depends(get_db)
):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    interaction = crud.update_interaction(db, interaction_id, updates)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return _serialize(interaction)


@router.get("/{interaction_id}", response_model=schemas.InteractionOut)
def get_interaction_endpoint(interaction_id: int, db: Session = Depends(get_db)):
    interaction = crud.get_interaction(db, interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return _serialize(interaction)


@router.get("/hcp/{hcp_name}", response_model=List[schemas.InteractionOut])
def list_for_hcp(hcp_name: str, db: Session = Depends(get_db)):
    interactions = crud.list_interactions_for_hcp(db, hcp_name, limit=20)
    return [_serialize(i) for i in interactions]
