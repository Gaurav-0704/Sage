import React, { useEffect, useState, useRef, useCallback } from "react";
import { api } from "../api";

const SUGGESTIONS = [
  "Show me the dashboard summary.",
  "Who has the highest outstanding fees?",
  "Add a new student named Riya Sharma to class 5 section A, parent Mr. Sharma, phone 9876543210.",
  "Increase the tuition fee for class 8 by 10% for academic year 2025-26.",
  "Create a Term 2 exam for class 10 on 2026-01-15.",
  "How much did we collect in cash today?",
];

export default function OwnerAI() {
  const [status, setStatus] = useState(null);
  const [tools, setTools]   = useState([]);
  const [conv, setConv]     = useState(null);
  const [conversations, setConversations] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput]   = useState("");
  const [busy, setBusy]     = useState(false);
  const [err, setErr]       = useState("");
  const [showHelp, setShowHelp] = useState(false);
  const bottomRef = useRef(null);

  const reload = useCallback((convId) => {
    Promise.all([
      api.get("/ai/status"),
      api.get("/ai/conversations"),
      convId ? api.get(`/ai/conversations/${convId}/messages`)
             : Promise.resolve({ data: [] }),
    ]).then(([s, c, m]) => {
      setStatus(s.data); setConversations(c.data); setMessages(m.data);
    }).catch((e) => setErr(e?.response?.data?.detail || "Failed"));
  }, []);

  useEffect(() => { reload(conv); }, [conv, reload]);
  useEffect(() => {
    if (status?.configured) api.get("/ai/tools").then((r) => setTools(r.data)).catch(() => {});
  }, [status?.configured]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async (e, override) => {
    e?.preventDefault();
    const text = override ?? input;
    if (!text.trim() || busy) return;
    setBusy(true); setErr("");
    try {
      const r = await api.post("/ai/chat",
                                { conversation_id: conv, message: text });
      setConv(r.data.conversation_id); setInput("");
      reload(r.data.conversation_id);
    } catch (e) { setErr(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  const remove = async (cid) => {
    if (!window.confirm("Delete this conversation?")) return;
    await api.delete(`/ai/conversations/${cid}`);
    if (cid === conv) { setConv(null); setMessages([]); }
    reload(null);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Assistant</h1>
          <p className="page-sub">
            Ask in plain English. The assistant will plan changes and wait for your
            approval — you control which actions actually run.
          </p>
        </div>
        <div className="flex gap-8 flex-wrap">
          <button className="btn btn-secondary" onClick={() => setShowHelp((v) => !v)}>
            {showHelp ? "Hide" : "What can it do?"}
          </button>
          <button className="btn btn-secondary"
                  onClick={() => { setConv(null); setMessages([]); }}>
            + New chat
          </button>
        </div>
      </div>

      {!status?.configured && (
        <div className="error-banner">
          Assistant not configured. Set the <code>ANTHROPIC_API_KEY</code> environment
          variable and restart the backend (<code>py run.py</code>). Get a key at
          console.anthropic.com.
        </div>
      )}

      {showHelp && tools.length > 0 && (
        <div className="card mb-16">
          <div className="card-title">What the assistant can do ({tools.length} actions)</div>
          <div className="grid grid-cols-2">
            {tools.map((t) => (
              <div key={t.name} style={{ padding: 8 }}>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <code style={{ background: "var(--surface-2)", padding: "2px 6px",
                                  borderRadius: 4, fontSize: 11 }}>{t.name}</code>
                  {t.destructive && <span className="pill red">destructive</span>}
                  {t.readonly && <span className="pill">read-only</span>}
                </div>
                <div className="text-3" style={{ fontSize: 12, marginTop: 4 }}>{t.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {err && <div className="error-banner">{err}</div>}

      <div className="ai-layout">
        {/* Past conversations */}
        <div className="card" style={{ padding: 12, maxHeight: "70vh", overflow: "auto" }}>
          <div className="card-title" style={{ marginBottom: 8 }}>Conversations</div>
          {conversations.length === 0 && (
            <div className="text-3" style={{ fontSize: 12 }}>No conversations yet.</div>
          )}
          {conversations.map((c) => (
            <div key={c.id} className="roster-row"
                 style={{
                   borderRadius: 8, marginBottom: 4, paddingTop: 8, paddingBottom: 8,
                   background: c.id === conv ? "var(--brand-50)" : "transparent",
                 }}
                 onClick={() => setConv(c.id)}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500,
                              whiteSpace: "nowrap", overflow: "hidden",
                              textOverflow: "ellipsis" }}>
                  {c.title}
                </div>
                <div className="text-3" style={{ fontSize: 10 }}>
                  {new Date(c.created_at).toLocaleDateString()}
                </div>
              </div>
              <button className="btn btn-secondary"
                      style={{ padding: "2px 8px", fontSize: 12, minHeight: "auto" }}
                      onClick={(e) => { e.stopPropagation(); remove(c.id); }}>×</button>
            </div>
          ))}
        </div>

        {/* Chat panel */}
        <div className="card" style={{ display: "flex", flexDirection: "column",
                                       padding: 0, minHeight: "70vh", maxHeight: "78vh" }}>
          <div style={{ flex: 1, overflow: "auto", padding: 18 }}>
            {messages.length === 0 && (
              <div style={{ padding: "40px 0", textAlign: "center" }}>
                <div style={{ fontSize: 36, marginBottom: 10 }}>💬</div>
                <div className="text-2" style={{ fontSize: 14 }}>
                  Ask the assistant anything about Nagarjuna High School.
                </div>
                <div className="text-3" style={{ fontSize: 12, marginTop: 6 }}>
                  Try one of these:
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6,
                              maxWidth: 540, margin: "12px auto 0" }}>
                  {SUGGESTIONS.map((s) => (
                    <button key={s} className="btn btn-secondary"
                            style={{ padding: "10px 12px", fontSize: 12,
                                      textAlign: "left", justifyContent: "flex-start" }}
                            onClick={() => send(null, s)}>{s}</button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m) => (
              <MessageBubble key={m.id} m={m} convId={conv} reload={() => reload(conv)}/>
            ))}
            <div ref={bottomRef}/>
          </div>

          <form onSubmit={send}
                style={{ display: "flex", gap: 8, padding: 14,
                          borderTop: "1px solid var(--border)" }}>
            <input className="input" placeholder="Ask the assistant…"
                   value={input} onChange={(e) => setInput(e.target.value)}
                   disabled={busy || !status?.configured}/>
            <button className="btn" disabled={busy || !input.trim() || !status?.configured}>
              {busy ? "Thinking…" : "Send"}
            </button>
          </form>
        </div>
      </div>

      <style>{`
        .ai-layout {
          display: grid;
          grid-template-columns: 240px 1fr;
          gap: 16px;
        }
        @media (max-width: 800px) {
          .ai-layout { grid-template-columns: 1fr; }
          .ai-layout > .card:first-child {
            max-height: 200px !important;
          }
        }
      `}</style>
    </div>
  );
}

/* ---------- One message bubble (user, system, or assistant + actions) ---------- */
function MessageBubble({ m, convId, reload }) {
  if (m.role === "user") {
    const isSystem = m.content.startsWith("[system]");
    return (
      <div style={{ display: "flex",
                     justifyContent: isSystem ? "center" : "flex-end",
                     marginBottom: 14 }}>
        <div style={{
          maxWidth: "82%",
          background: isSystem ? "var(--surface-2)" : "var(--brand-50)",
          color: isSystem ? "var(--text-2)" : "var(--text)",
          padding: "10px 14px", borderRadius: 14,
          fontSize: 13.5, lineHeight: 1.55,
          fontStyle: isSystem ? "italic" : "normal",
          fontFamily: isSystem ? "ui-monospace, monospace" : "inherit",
          whiteSpace: "pre-wrap", overflowWrap: "break-word",
        }}>{m.content.replace(/^\[system\]\s*/, "")}</div>
      </div>
    );
  }

  const actions = m.actions ? JSON.parse(m.actions) : [];
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
        <div className="avatar" style={{ width: 30, height: 30, fontSize: 12,
                                          flexShrink: 0 }}>A</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          {m.content && (
            <div style={{ background: "var(--surface-2)",
                           padding: "10px 14px", borderRadius: 14,
                           fontSize: 13.5, lineHeight: 1.55,
                           whiteSpace: "pre-wrap", overflowWrap: "break-word" }}>
              {m.content}
            </div>
          )}
          {actions.length > 0 && (
            <ActionsPanel
              messageId={m.id}
              convId={convId}
              actions={actions}
              executed={m.executed}
              onApplied={reload}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ---------- Per-action approval panel ---------- */
function ActionsPanel({ messageId, convId, actions, executed, onApplied }) {
  // approved: set of action ids selected for execution
  const [approved, setApproved] = useState(() => new Set(
    // default: include all non-destructive
    actions.filter((a) => !a.destructive).map((a) => a.id)
  ));
  const [overrides, setOverrides] = useState({});
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  if (executed) {
    return (
      <div className="success-banner" style={{ marginTop: 10, marginBottom: 0 }}>
        ✓ Actions executed.
      </div>
    );
  }

  const toggle = (id) => {
    const next = new Set(approved);
    next.has(id) ? next.delete(id) : next.add(id);
    setApproved(next);
  };

  const apply = async () => {
    if (approved.size === 0) {
      setErr("Pick at least one action to apply.");
      return;
    }
    const destructiveCount = actions.filter(
      (a) => approved.has(a.id) && a.destructive).length;
    if (destructiveCount > 0) {
      if (!window.confirm(
        `${destructiveCount} destructive action(s) will run. ` +
        `This cannot be undone. Continue?`)) return;
    }
    setBusy(true); setErr("");
    try {
      await api.post("/ai/execute", {
        conversation_id: convId,
        message_id: messageId,
        approved_action_ids: Array.from(approved),
        overrides,
      });
      onApplied();
    } catch (e) { setErr(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div style={{ marginTop: 10, padding: 14, borderRadius: 12,
                   background: "var(--surface-3)",
                   border: "1px solid var(--border-2)" }}>
      <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 10,
                     color: "var(--brand-500)", textTransform: "uppercase",
                     letterSpacing: ".1em" }}>
        Proposed actions ({actions.length}) · {approved.size} selected
      </div>
      {err && <div className="error-banner">{err}</div>}

      {actions.map((a, i) => (
        <div key={a.id} style={{
          padding: "10px 0",
          borderTop: i ? "1px solid var(--border)" : "none",
        }}>
          <label style={{ display: "flex", alignItems: "flex-start",
                           gap: 10, cursor: "pointer" }}>
            <input type="checkbox" checked={approved.has(a.id)}
                   onChange={() => toggle(a.id)}
                   style={{ marginTop: 4, transform: "scale(1.2)" }}/>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6,
                             flexWrap: "wrap" }}>
                <code style={{ background: "var(--surface-2)",
                                padding: "2px 6px", borderRadius: 4,
                                fontSize: 12, fontWeight: 600 }}>
                  {a.name}
                </code>
                {a.destructive && <span className="pill red">destructive</span>}
                {a.readonly && <span className="pill">read-only</span>}
                <button className="btn btn-secondary"
                        style={{ padding: "2px 8px", fontSize: 11,
                                  marginLeft: "auto", minHeight: "auto" }}
                        onClick={(e) => { e.preventDefault();
                                          setEditing(editing === a.id ? null : a.id); }}>
                  {editing === a.id ? "Done" : "Edit"}
                </button>
              </div>

              {editing === a.id ? (
                <textarea
                  className="input"
                  rows={Math.min(8, Object.keys(a.input).length + 2)}
                  style={{ marginTop: 8, fontFamily: "ui-monospace, monospace",
                            fontSize: 12 }}
                  value={JSON.stringify(overrides[a.id] || a.input, null, 2)}
                  onChange={(e) => {
                    try {
                      const parsed = JSON.parse(e.target.value);
                      setOverrides({ ...overrides, [a.id]: parsed });
                    } catch {
                      // leave as-is until valid
                    }
                  }}
                />
              ) : (
                <pre style={{ margin: "6px 0 0", fontSize: 11.5,
                               color: "var(--text-2)",
                               fontFamily: "ui-monospace, monospace",
                               whiteSpace: "pre-wrap",
                               overflowWrap: "break-word" }}>
                  {JSON.stringify(overrides[a.id] || a.input, null, 2)}
                </pre>
              )}
            </div>
          </label>
        </div>
      ))}

      <div className="flex gap-8" style={{ marginTop: 12, justifyContent: "flex-end",
                                            flexWrap: "wrap" }}>
        <button className="btn btn-secondary"
                onClick={() => setApproved(new Set())}
                disabled={busy || approved.size === 0}>
          Deselect all
        </button>
        <button className="btn btn-secondary"
                onClick={() => setApproved(new Set(actions.map((a) => a.id)))}
                disabled={busy || approved.size === actions.length}>
          Select all
        </button>
        <button className="btn" onClick={apply}
                disabled={busy || approved.size === 0}>
          {busy ? "Applying…" : `✓ Apply ${approved.size} action(s)`}
        </button>
      </div>
    </div>
  );
}
