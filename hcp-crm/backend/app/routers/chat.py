import json

from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.agent.graph import agent_app
from app.routers.interactions import _serialize

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Naive in-memory session store keyed by session_id -> list[BaseMessage].
# Good enough for the assignment; swap for Redis/DB-backed history in prod.
_SESSIONS: dict[str, list] = {}


@router.post("", response_model=schemas.ChatResponse)
def chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    history = _SESSIONS.setdefault(payload.session_id, [])
    history.append(HumanMessage(content=payload.message))

    result = agent_app.invoke({"messages": history})
    messages = result["messages"]
    _SESSIONS[payload.session_id] = messages

    tool_calls_used = []
    interaction_out = None
    suggested_followups = []
    logged_interaction_id = None

    for m in messages:
        if isinstance(m, ToolMessage):
            tool_calls_used.append(m.name)
            try:
                data = json.loads(m.content)
            except (json.JSONDecodeError, TypeError):
                continue
            if m.name == "log_interaction" and isinstance(data, dict):
                logged_interaction_id = data.get("interaction_id")
            if m.name == "suggest_followups" and isinstance(data, list):
                suggested_followups = data

    if logged_interaction_id:
        interaction = crud.get_interaction(db, logged_interaction_id)
        if interaction:
            interaction_out = _serialize(interaction)
            if not suggested_followups:
                suggested_followups = interaction.ai_suggested_followups or []

    final_ai_messages = [m for m in messages if isinstance(m, AIMessage) and m.content]
    reply = final_ai_messages[-1].content if final_ai_messages else "Done."

    return schemas.ChatResponse(
        reply=reply,
        tool_calls=tool_calls_used,
        interaction=interaction_out,
        suggested_followups=suggested_followups,
    )
