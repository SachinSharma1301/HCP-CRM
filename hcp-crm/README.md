# AI-First CRM — HCP Module: Log Interaction Screen

A working implementation of the "Log HCP Interaction" screen for an AI-first
CRM, built for pharmaceutical field representatives. Reps can log an
interaction with a Healthcare Professional (HCP) either through a **structured
form** or a **conversational chat interface** powered by a **LangGraph**
agent running on **Groq** LLMs.

## Tech stack

| Layer     | Choice |
|-----------|--------|
| Frontend  | React + Redux Toolkit (Vite), Google Inter font |
| Backend   | Python, FastAPI |
| AI Agent  | LangGraph (ReAct-style tool-calling agent) |
| LLMs      | Groq `gemma2-9b-it` (primary), `llama-3.3-70b-versatile` (fallback / richer context) |
| Database  | SQLAlchemy ORM — SQLite by default, drop-in Postgres/MySQL support |

## Project structure

```
hcp-crm/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, router registration
│   │   ├── config.py          # env-based settings (Groq key, DB url, ...)
│   │   ├── database.py        # SQLAlchemy engine/session
│   │   ├── models.py          # HCP, Interaction, Material, ChatMessage
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── crud.py            # DB helpers shared by REST routes + agent tools
│   │   ├── agent/
│   │   │   ├── llm.py         # Groq LLM wrapper (primary + fallback)
│   │   │   ├── tools.py       # The 5 LangGraph tools
│   │   │   └── graph.py       # LangGraph StateGraph (the agent itself)
│   │   └── routers/
│   │       ├── interactions.py  # Structured-form CRUD endpoints
│   │       ├── hcp.py            # HCP + materials lookup endpoints
│   │       └── chat.py           # Drives the LangGraph agent for the chat UI
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LogInteractionForm.jsx  # Structured form (left panel)
│   │   │   ├── ChatAssistant.jsx       # AI chat (right panel)
│   │   │   └── Header.jsx
│   │   ├── store/                      # Redux Toolkit slices
│   │   ├── api/client.js               # Axios API client
│   │   └── App.jsx
│   └── package.json
└── docker-compose.yml   # optional one-command run (Postgres + backend + frontend)
```

## The LangGraph Agent

`app/agent/graph.py` builds a standard ReAct-style loop with `langgraph`:

```
START → agent (LLM decides: reply or call a tool) → tools → agent → ... → END
```

The LLM is bound to **5 tools** (`app/agent/tools.py`), satisfying the
assignment's requirement of a minimum of five sales-related tools, including
the two mandatory ones:

1. **`log_interaction`** *(mandatory)* — Takes the rep's free-text notes
   (e.g. *"Met Dr. Smith, discussed Product X efficacy, positive sentiment,
   shared brochure"*). Calls the LLM twice: once with a strict-JSON extraction
   prompt to pull out `hcp_name`, `topics_discussed`, `materials_shared`,
   `samples_distributed`, `sentiment`, `outcomes`, `follow_up_actions`; and
   once to produce a one-line AI summary. Saves the structured result to the
   database via `crud.create_interaction` and returns the new interaction id.

2. **`edit_interaction`** *(mandatory)* — Takes an `interaction_id` and a
   JSON string of field updates (e.g. `{"sentiment": "positive"}`) and patches
   the existing row via `crud.update_interaction`.

3. **`get_hcp_history`** — Looks up the most recent logged interactions for a
   given HCP by name, giving the agent (and the rep) context before/after a
   meeting.

4. **`suggest_followups`** — Given a logged interaction and that HCP's recent
   history, prompts the LLM for 2–4 concrete follow-up actions (matching the
   mockup's "AI Suggested Follow-ups" panel, e.g. *"Schedule follow-up
   meeting in 2 weeks"*, *"Send OncoBoost Phase III PDF"*). Persists the
   suggestions on the interaction row.

5. **`search_materials`** — Searches the catalog of marketing materials /
   drug samples that can be attached to an interaction, used both by the chat
   agent and the "Search/Add" control in the structured form.

Each tool is a plain Python function (`@tool` from `langchain_core.tools`)
with a docstring the LLM reads to decide when/how to call it — this is what
LangGraph's `ToolNode` executes.

### Why two Groq models?

* `gemma2-9b-it` is the **primary** model for the main agent loop and the
  extraction/summarization calls inside `log_interaction` — fast and cheap,
  good for tightly-scoped structured output.
* `llama-3.3-70b-versatile` is used as a **fallback** if the primary call
  fails (e.g. rate limiting) and for `suggest_followups`, which benefits from
  slightly stronger reasoning over multi-turn HCP history.

See `app/agent/llm.py`.

## Running locally

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set GROQ_API_KEY (create one at https://console.groq.com/keys)

uvicorn app.main:app --reload --port 8000
```

By default this uses SQLite (`hcp_crm.db`, created automatically on first
run) — zero external DB setup required. To use Postgres or MySQL instead,
just change `DATABASE_URL` in `.env`:

```
# Postgres
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/hcp_crm

# MySQL
DATABASE_URL=mysql+pymysql://root:root@localhost:3306/hcp_crm
```

API docs available at `http://localhost:8000/docs`.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:5173`.

### 3. (Optional) One command with Docker Compose

```bash
docker compose up --build
```

This spins up Postgres, the FastAPI backend, and the Vite dev server for the
frontend. Set `GROQ_API_KEY` in `backend/.env` first.

## Using the screen

* **Structured form (left panel):** Fill in HCP name, interaction type,
  date/time, attendees, topics, materials/samples, sentiment, outcomes and
  follow-ups, then click **Log Interaction**. On save, the backend
  automatically calls the `suggest_followups` tool and displays AI-suggested
  next steps.
* **AI chat (right panel):** Type a free-text description of the interaction
  (e.g. *"Met Dr. Sharma, discussed OncoBoost Phase III data, she was
  positive and asked for the PDF"*). The LangGraph agent will call
  `log_interaction` to extract structured fields and save it, then
  `suggest_followups` to propose next steps — both shown in the chat and
  mirrored into the structured form via Redux (`hydrateFromAgent`).

## API summary

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/interactions` | Create interaction from structured form |
| PATCH | `/api/interactions/{id}` | Edit an interaction |
| GET | `/api/interactions/{id}` | Fetch one interaction |
| GET | `/api/interactions/hcp/{hcp_name}` | History for an HCP |
| GET | `/api/hcps?q=` | Search/list HCPs |
| GET | `/api/materials?q=` | Search materials/samples |
| POST | `/api/chat` | Send a message to the LangGraph agent |
| GET | `/api/health` | Health check |

## Notes / assumptions

* Auth, multi-tenant workspaces, and offline/voice-note transcription are out
  of scope for this assignment and stubbed out or omitted; the "Summarize
  from Voice Note" button in the mockup is a UI affordance only.
* SQLite is used as the zero-config default database so the reviewer can run
  the project immediately; switching to Postgres/MySQL is a one-line env
  change (see above) since the code is plain SQLAlchemy.
* Chat history is kept in an in-memory dict keyed by a client-generated
  session id (`app/routers/chat.py`) — fine for a demo/assignment; swap for a
  persistent store for production use.
