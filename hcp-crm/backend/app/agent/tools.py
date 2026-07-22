import json
from typing import List, Optional

from langchain_core.tools import tool

from app import crud
from app.database import SessionLocal
from app.agent.llm import invoke_with_fallback


def _db():
    return SessionLocal()


EXTRACTION_SYSTEM_PROMPT = """You are a life-science CRM assistant. Extract structured
fields from a field representative's free-text note about a Healthcare Professional (HCP)
interaction. Respond ONLY with strict JSON, no markdown fences, no commentary, matching
this schema:
{
  "hcp_name": string,
  "interaction_type": one of ["Meeting","Call","Email","Conference"],
  "attendees": string,
  "topics_discussed": string,
  "materials_shared": [string],
  "samples_distributed": [string],
  "sentiment": one of ["positive","neutral","negative"],
  "outcomes": string,
  "follow_up_actions": string
}
If a field is unknown, use an empty string or empty list. Never invent an HCP name; if none
is mentioned, use "Unknown HCP".
"""


@tool
def log_interaction(
    raw_notes: str,
    hcp_name: Optional[str] = None,
    interaction_type: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
) -> str:
    """Log a new HCP interaction. Pass the representative's free-text notes
    (e.g. "Met Dr. Smith, discussed Product X efficacy, positive sentiment,
    shared brochure") as `raw_notes`. This tool uses the LLM to extract
    entities (HCP name, topics, materials, samples, sentiment, outcomes,
    follow-ups) and a short AI summary, then saves the interaction to the
    database. Optionally override hcp_name/interaction_type/date/time if
    already known (e.g. from the structured form). Returns a JSON string
    describing the saved interaction, including its id.
    """
    db = _db()
    try:
        extraction_msg = [
            ("system", EXTRACTION_SYSTEM_PROMPT),
            ("user", raw_notes),
        ]
        result = invoke_with_fallback(extraction_msg)
        try:
            extracted = json.loads(result.content)
        except json.JSONDecodeError:
            extracted = {
                "hcp_name": hcp_name or "Unknown HCP",
                "interaction_type": interaction_type or "Meeting",
                "attendees": "",
                "topics_discussed": raw_notes,
                "materials_shared": [],
                "samples_distributed": [],
                "sentiment": "neutral",
                "outcomes": "",
                "follow_up_actions": "",
            }

        final_hcp_name = hcp_name or extracted.get("hcp_name") or "Unknown HCP"

        summary_msg = [
            (
                "system",
                "Summarize the following HCP interaction in one crisp sentence "
                "for a CRM feed. Respond with plain text only.",
            ),
            ("user", raw_notes),
        ]
        summary = invoke_with_fallback(summary_msg).content.strip()

        data = {
            "interaction_type": interaction_type or extracted.get("interaction_type", "Meeting"),
            "date": date,
            "time": time,
            "attendees": extracted.get("attendees", ""),
            "topics_discussed": extracted.get("topics_discussed", raw_notes),
            "materials_shared": extracted.get("materials_shared", []),
            "samples_distributed": extracted.get("samples_distributed", []),
            "sentiment": extracted.get("sentiment", "neutral"),
            "outcomes": extracted.get("outcomes", ""),
            "follow_up_actions": extracted.get("follow_up_actions", ""),
            "ai_summary": summary,
        }
        interaction = crud.create_interaction(db, final_hcp_name, data)
        return json.dumps(
            {
                "status": "logged",
                "interaction_id": interaction.id,
                "hcp_name": final_hcp_name,
                "summary": summary,
                "sentiment": data["sentiment"],
            }
        )
    finally:
        db.close()


@tool
def edit_interaction(
    interaction_id: int,
    field_updates_json: str,
) -> str:
    """Edit/modify a previously logged interaction. `interaction_id` is the id
    returned by log_interaction. `field_updates_json` is a JSON string with
    the fields to change, e.g. '{"outcomes": "Agreed to trial", "sentiment":
    "positive"}'. Allowed fields: interaction_type, date, time, attendees,
    topics_discussed, materials_shared, samples_distributed, sentiment,
    outcomes, follow_up_actions. Returns a JSON string of the updated
    interaction, or an error message if not found.
    """
    db = _db()
    try:
        try:
            updates = json.loads(field_updates_json)
        except json.JSONDecodeError:
            return json.dumps({"status": "error", "message": "field_updates_json is not valid JSON"})

        interaction = crud.update_interaction(db, interaction_id, updates)
        if not interaction:
            return json.dumps({"status": "error", "message": f"No interaction with id {interaction_id}"})

        return json.dumps(
            {
                "status": "updated",
                "interaction_id": interaction.id,
                "updated_fields": list(updates.keys()),
            }
        )
    finally:
        db.close()


@tool
def get_hcp_history(hcp_name: str, limit: int = 5) -> str:
    """Retrieve the most recent logged interactions for a given HCP by name.
    Useful for giving the rep context before a meeting, or for deciding what
    follow-up to suggest. Returns a JSON array of past interactions
    (most recent first).
    """
    db = _db()
    try:
        interactions = crud.list_interactions_for_hcp(db, hcp_name, limit=limit)
        out = [
            {
                "id": i.id,
                "date": i.date,
                "interaction_type": i.interaction_type,
                "topics_discussed": i.topics_discussed,
                "sentiment": i.sentiment.value if hasattr(i.sentiment, "value") else i.sentiment,
                "outcomes": i.outcomes,
                "follow_up_actions": i.follow_up_actions,
            }
            for i in interactions
        ]
        return json.dumps(out)
    finally:
        db.close()


@tool
def suggest_followups(interaction_id: int) -> str:
    """Generate 2-4 concrete, actionable follow-up suggestions (e.g. schedule
    a meeting, send a specific brochure, add to an advisory board) for a
    logged interaction, using the LLM and the HCP's interaction history for
    context. Saves the suggestions onto the interaction record and returns
    them as a JSON array of strings.
    """
    db = _db()
    try:
        interaction = crud.get_interaction(db, interaction_id)
        if not interaction:
            return json.dumps({"status": "error", "message": f"No interaction with id {interaction_id}"})

        history = crud.list_interactions_for_hcp(db, interaction.hcp.name, limit=5)
        history_text = "\n".join(
            f"- {h.date or ''} ({h.sentiment}): {h.topics_discussed or ''} -> {h.outcomes or ''}"
            for h in history
        )

        prompt = [
            (
                "system",
                "You are a life-science CRM assistant helping a pharma field "
                "representative plan next steps after an HCP interaction. "
                "Given the latest interaction and recent history, propose 2 to 4 "
                "short, concrete follow-up actions (e.g. 'Schedule follow-up "
                "meeting in 2 weeks', 'Send OncoBoost Phase III PDF', 'Add Dr. X "
                "to advisory board invite list'). Respond ONLY with a JSON array "
                "of strings, no commentary.",
            ),
            (
                "user",
                f"Latest interaction:\nTopics: {interaction.topics_discussed}\n"
                f"Sentiment: {interaction.sentiment}\nOutcomes: {interaction.outcomes}\n\n"
                f"Recent history:\n{history_text or 'None'}",
            ),
        ]
        result = invoke_with_fallback(prompt, temperature=0.4)
        try:
            suggestions = json.loads(result.content)
            if not isinstance(suggestions, list):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            suggestions = [
                line.strip("- ").strip()
                for line in result.content.splitlines()
                if line.strip()
            ][:4]

        crud.update_interaction(db, interaction_id, {"ai_suggested_followups": suggestions})
        return json.dumps(suggestions)
    finally:
        db.close()


@tool
def search_materials(query: str = "") -> str:
    """Search the available marketing materials and drug samples that can be
    attached to an interaction (e.g. brochures, clinical PDFs, sample packs).
    Pass an empty string to list everything. Returns a JSON array of matching
    item names.
    """
    db = _db()
    try:
        crud.seed_materials(db)
        results = crud.search_materials(db, query)
        return json.dumps(results)
    finally:
        db.close()


ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    get_hcp_history,
    suggest_followups,
    search_materials,
]
