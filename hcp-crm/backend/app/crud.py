from typing import List, Optional
from sqlalchemy.orm import Session

from app import models


DEFAULT_MATERIALS = [
    "OncoBoost Phase III PDF",
    "Product X Efficacy Brochure",
    "Cardio-Safe Dosage Card",
    "Patient Onboarding Kit",
    "Formulary Comparison Sheet",
]

DEFAULT_SAMPLES = [
    "OncoBoost 50mg Sample Pack",
    "Product X Starter Sample",
    "Cardio-Safe Trial Pack",
]


def get_or_create_hcp(db: Session, name: str) -> models.HCP:
    hcp = db.query(models.HCP).filter(models.HCP.name.ilike(name.strip())).first()
    if hcp:
        return hcp
    hcp = models.HCP(name=name.strip())
    db.add(hcp)
    db.commit()
    db.refresh(hcp)
    return hcp


def create_interaction(db: Session, hcp_name: str, data: dict) -> models.Interaction:
    hcp = get_or_create_hcp(db, hcp_name)
    interaction = models.Interaction(
        hcp_id=hcp.id,
        interaction_type=data.get("interaction_type", "Meeting"),
        date=data.get("date"),
        time=data.get("time"),
        attendees=data.get("attendees"),
        topics_discussed=data.get("topics_discussed"),
        materials_shared=data.get("materials_shared", []) or [],
        samples_distributed=data.get("samples_distributed", []) or [],
        sentiment=data.get("sentiment", "neutral"),
        outcomes=data.get("outcomes"),
        follow_up_actions=data.get("follow_up_actions"),
        ai_suggested_followups=data.get("ai_suggested_followups", []) or [],
        ai_summary=data.get("ai_summary"),
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


def update_interaction(
    db: Session, interaction_id: int, updates: dict
) -> Optional[models.Interaction]:
    interaction = (
        db.query(models.Interaction)
        .filter(models.Interaction.id == interaction_id)
        .first()
    )
    if not interaction:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(interaction, key):
            setattr(interaction, key, value)
    db.commit()
    db.refresh(interaction)
    return interaction


def get_interaction(db: Session, interaction_id: int) -> Optional[models.Interaction]:
    return (
        db.query(models.Interaction)
        .filter(models.Interaction.id == interaction_id)
        .first()
    )


def list_interactions_for_hcp(
    db: Session, hcp_name: str, limit: int = 10
) -> List[models.Interaction]:
    hcp = db.query(models.HCP).filter(models.HCP.name.ilike(hcp_name.strip())).first()
    if not hcp:
        return []
    return (
        db.query(models.Interaction)
        .filter(models.Interaction.hcp_id == hcp.id)
        .order_by(models.Interaction.created_at.desc())
        .limit(limit)
        .all()
    )


def search_materials(db: Session, query: str, category: Optional[str] = None) -> List[str]:
    db_materials = db.query(models.Material)
    if category:
        db_materials = db_materials.filter(models.Material.category == category)
    names = [m.name for m in db_materials.all()]

    if not names:
        names = DEFAULT_MATERIALS if category == "material" else DEFAULT_SAMPLES if category == "sample" else DEFAULT_MATERIALS + DEFAULT_SAMPLES

    query_l = query.lower().strip()
    if not query_l:
        return names
    return [m for m in names if query_l in m.lower()]


def seed_materials(db: Session):
    if db.query(models.Material).count() > 0:
        return
    for name in DEFAULT_MATERIALS:
        db.add(models.Material(name=name, category="material"))
    for name in DEFAULT_SAMPLES:
        db.add(models.Material(name=name, category="sample"))
    db.commit()
