import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  updateField,
  addMaterial,
  removeMaterial,
  addSample,
  removeSample,
  submitInteraction,
  resetForm,
} from "../store/interactionsSlice";
import { searchMaterials } from "../api/client";

const INTERACTION_TYPES = ["Meeting", "Call", "Email", "Conference"];

function ChipPicker({ label, placeholder, selected, onAdd, onRemove, category }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const runSearch = async (q) => {
    setQuery(q);
    setLoadError(null);
    try {
      const found = await searchMaterials(q, category);
      setResults((found || []).filter((r) => !selected.includes(r)));
      setOpen(true);
    } catch (err) {
      console.error(`Failed to search ${label}:`, err);
      setResults([]);
      setLoadError("Couldn't load suggestions — you can still type your own and press Enter.");
      setOpen(true);
    }
  };

  const handleFocus = () => runSearch(query);

  const pick = (item) => {
    onAdd(item);
    setQuery("");
    setResults([]);
    setOpen(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (query.trim()) pick(query.trim());
    }
  };

  return (
    <div style={{ marginBottom: 10 }}>
      <div className="materials-row" style={{ position: "relative" }}>
        <span className="label">{label}</span>
        <input
          placeholder={placeholder}
          value={query}
          onFocus={handleFocus}
          onChange={(e) => runSearch(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
        />
      </div>

      {open && (
        <div
          className="panel"
          style={{
            padding: 6,
            marginTop: 4,
            marginLeft: 168,
            maxWidth: 260,
            boxShadow: "0 4px 10px rgba(16,24,40,0.12)",
          }}
        >
          {loadError && (
            <div style={{ fontSize: 12, color: "var(--color-negative)", padding: "4px 8px" }}>
              {loadError}
            </div>
          )}
          {!loadError && results.length === 0 && (
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", padding: "4px 8px" }}>
              No matches — type your own and press Enter to add it.
            </div>
          )}
          {results.map((r) => (
            <div
              key={r}
              onMouseDown={() => pick(r)}
              style={{
                padding: "6px 8px",
                fontSize: 13,
                cursor: "pointer",
                borderRadius: 6,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "#f1f4fb")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              {r}
            </div>
          ))}
        </div>
      )}

      {selected.length === 0 ? (
        <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 6, marginLeft: 168 }}>
          No {label.toLowerCase()} added
        </div>
      ) : (
        <div className="chip-row" style={{ marginLeft: 168 }}>
          {selected.map((item) => (
            <span key={item} className="chip">
              {item}
              <button
                type="button"
                onClick={() => onRemove(item)}
                aria-label={`Remove ${item}`}
                style={{
                  marginLeft: 6,
                  border: "none",
                  background: "transparent",
                  color: "var(--color-primary-dark)",
                  cursor: "pointer",
                  fontWeight: 700,
                  padding: 0,
                }}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function LogInteractionForm() {
  const dispatch = useDispatch();
  const { form, status, lastSaved, error } = useSelector((s) => s.interactions);

  const set = (field) => (e) =>
    dispatch(updateField({ field, value: e.target.value }));

  const handleSubmit = (e) => {
    e.preventDefault();
    dispatch(submitInteraction());
  };

  return (
    <form className="panel" onSubmit={handleSubmit}>
      <h2>Interaction Details</h2>

      {status === "saved" && lastSaved && (
        <div className="status-banner saved">
          Saved interaction #{lastSaved.id} for review. AI summary: {lastSaved.ai_summary || "—"}
        </div>
      )}
      {status === "error" && (
        <div className="status-banner error">Failed to save: {error}</div>
      )}

      <div className="form-row">
        <div className="field">
          <label>HCP Name</label>
          <input
            placeholder="Search or select HCP..."
            value={form.hcpName}
            onChange={set("hcpName")}
            required
          />
        </div>
        <div className="field">
          <label>Interaction Type</label>
          <select value={form.interactionType} onChange={set("interactionType")}>
            {INTERACTION_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="form-row">
        <div className="field">
          <label>Date</label>
          <input type="date" value={form.date} onChange={set("date")} />
        </div>
        <div className="field">
          <label>Time</label>
          <input type="time" value={form.time} onChange={set("time")} />
        </div>
      </div>

      <div className="field" style={{ marginBottom: 14 }}>
        <label>Attendees</label>
        <input
          placeholder="Enter names or search..."
          value={form.attendees}
          onChange={set("attendees")}
        />
      </div>

      <div className="field" style={{ marginBottom: 14 }}>
        <label>Topics Discussed</label>
        <textarea
          placeholder="Enter key discussion points..."
          value={form.topicsDiscussed}
          onChange={set("topicsDiscussed")}
        />
      </div>

      <div className="field" style={{ marginBottom: 14 }}>
        <label>Materials Shared / Samples Distributed</label>

        <ChipPicker
          label="Materials Shared"
          placeholder="Search materials..."
          category="material"
          selected={form.materialsShared}
          onAdd={(m) => dispatch(addMaterial(m))}
          onRemove={(m) => dispatch(removeMaterial(m))}
        />

        <ChipPicker
          label="Samples Distributed"
          placeholder="Search samples..."
          category="sample"
          selected={form.samplesDistributed}
          onAdd={(s) => dispatch(addSample(s))}
          onRemove={(s) => dispatch(removeSample(s))}
        />
      </div>

      <div className="field" style={{ marginBottom: 14 }}>
        <label>Observed/Inferred HCP Sentiment</label>
        <div className="sentiment-row">
          {["positive", "neutral", "negative"].map((s) => (
            <label key={s}>
              <input
                type="radio"
                name="sentiment"
                value={s}
                checked={form.sentiment === s}
                onChange={set("sentiment")}
              />
              {s[0].toUpperCase() + s.slice(1)}
            </label>
          ))}
        </div>
      </div>

      <div className="field" style={{ marginBottom: 14 }}>
        <label>Outcomes</label>
        <textarea
          placeholder="Key outcomes or agreements..."
          value={form.outcomes}
          onChange={set("outcomes")}
        />
      </div>

      <div className="field" style={{ marginBottom: 14 }}>
        <label>Follow-up Actions</label>
        <textarea
          placeholder="Enter next steps or tasks..."
          value={form.followUpActions}
          onChange={set("followUpActions")}
        />
      </div>

      {lastSaved?.ai_suggested_followups?.length > 0 && (
        <div className="ai-followups">
          <div className="title">AI Suggested Follow-ups:</div>
          <ul>
            {lastSaved.ai_suggested_followups.map((f, idx) => (
              <li key={idx}>{f}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
        <button type="submit" className="btn btn-primary" disabled={status === "saving"}>
          {status === "saving" ? "Saving..." : "Log Interaction"}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => dispatch(resetForm())}
        >
          Clear
        </button>
      </div>
    </form>
  );
}