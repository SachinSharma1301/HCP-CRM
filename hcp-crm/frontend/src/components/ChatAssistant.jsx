import { useState, useRef, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { sendMessage } from "../store/chatSlice";
import { hydrateFromAgent } from "../store/interactionsSlice";

export default function ChatAssistant() {
  const dispatch = useDispatch();
  const { messages, status, lastInteraction, suggestedFollowups } = useSelector(
    (s) => s.chat
  );
  const [draft, setDraft] = useState("");
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages]);

  useEffect(() => {
    if (lastInteraction) {
      dispatch(hydrateFromAgent(lastInteraction));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastInteraction]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!draft.trim()) return;
    const text = draft;
    setDraft("");
    dispatch(sendMessage(text));
  };

  return (
    <div className="panel chat-panel">
      <div className="chat-header">
        <span className="dot" />
        <div>
          <div style={{ fontWeight: 600, fontSize: 13 }}>AI Assistant</div>
          <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
            Log interaction via chat
          </div>
        </div>
      </div>

      <div className="chat-messages" ref={listRef}>
        {messages.map((m, idx) => (
          <div key={idx} className={`chat-bubble ${m.role}`}>
            {m.content}
          </div>
        ))}
        {status === "loading" && (
          <div className="chat-bubble assistant">Thinking…</div>
        )}
      </div>

      {suggestedFollowups.length > 0 && (
        <div className="ai-followups">
          <div className="title">AI Suggested Follow-ups:</div>
          <ul>
            {suggestedFollowups.map((f, idx) => (
              <li key={idx}>{f}</li>
            ))}
          </ul>
        </div>
      )}

      <form className="chat-input-row" onSubmit={handleSend}>
        <input
          placeholder="Describe interaction..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button type="submit" className="btn btn-primary" disabled={status === "loading"}>
          Log
        </button>
      </form>
    </div>
  );
}
