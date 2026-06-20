import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api";

const COLOR_PRESETS = [
  "#2f6bff","#16a34a","#d97706","#dc2626","#7c3aed",
  "#0891b2","#9333ea","#ea580c","#525252","#db2777",
];
const ICON_PRESETS = ["💰","📚","🚌","📖","👕","👨‍🏫","💡","📦","🔧","🍽","🏃","🎨","💻","📝"];
const EXPENSE_CATEGORIES = ["salary","utilities","supplies","maintenance","transport","other"];

export default function Tiles() {
  const [tiles, setTiles] = useState([]);
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    api.get("/tiles/all")
      .then((r) => setTiles(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);
  useEffect(load, [load]);

  const remove = async (id) => {
    if (!window.confirm("Delete this tile?")) return;
    await api.delete(`/tiles/${id}`); load();
  };

  const toggleActive = async (t) => {
    await api.put(`/tiles/${t.id}`, { active: !t.active });
    load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Quick Tiles</h1>
          <p className="page-sub">Customize what Staff sees on their dashboard.</p>
        </div>
        <button className="btn" onClick={() => setCreating(true)}>+ Add tile</button>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div className="grid grid-cols-3">
        {tiles.map((t) => (
          <div key={t.id} className="card" style={{ position: "relative" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
              <div style={{
                width: 48, height: 48, borderRadius: 12,
                background: t.color, color: "white",
                display: "grid", placeItems: "center", fontSize: 22,
              }}>{t.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700 }}>{t.label}</div>
                <div className="text-3" style={{ fontSize: 12 }}>
                  {t.kind === "payment" ? `Fee head: ${t.fee_head || "—"}` : `Category: ${t.category}`}
                </div>
              </div>
              <span className={"pill " + (t.active ? "green" : "")}>
                {t.active ? "active" : "off"}
              </span>
            </div>
            <div className="flex gap-8">
              <button className="btn btn-secondary" style={{ padding: "6px 10px", fontSize: 12 }}
                      onClick={() => setEditing(t)}>Edit</button>
              <button className="btn btn-secondary" style={{ padding: "6px 10px", fontSize: 12 }}
                      onClick={() => toggleActive(t)}>{t.active ? "Disable" : "Enable"}</button>
              <button className="btn btn-danger" style={{ padding: "6px 10px", fontSize: 12, marginLeft: "auto" }}
                      onClick={() => remove(t.id)}>Delete</button>
            </div>
          </div>
        ))}
        {tiles.length === 0 && (
          <div className="empty" style={{ gridColumn: "1 / -1" }}>No tiles yet — add one to get started.</div>
        )}
      </div>

      {(creating || editing) && (
        <TileModal
          tile={editing}
          onClose={() => { setEditing(null); setCreating(false); }}
          onSaved={() => { setEditing(null); setCreating(false); load(); }}
        />
      )}
    </div>
  );
}

function TileModal({ tile, onClose, onSaved }) {
  const editing = !!tile;
  const [f, setF] = useState(() => tile || {
    label: "", kind: "payment", fee_head: "", category: "other",
    icon: "💰", color: "#2f6bff", sort_order: 0, active: true,
  });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const body = {
        label: f.label, kind: f.kind,
        fee_head: f.kind === "payment" ? (f.fee_head || f.label) : null,
        category: f.kind === "expense" ? f.category : null,
        icon: f.icon, color: f.color,
        sort_order: Number(f.sort_order) || 0,
        active: f.active !== false,
      };
      if (editing) await api.put(`/tiles/${tile.id}`, body);
      else         await api.post("/tiles", body);
      onSaved();
    } catch (e) { setErr(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={save}>
        <h3>{editing ? "Edit tile" : "New tile"}</h3>
        {err && <div className="error-banner">{err}</div>}

        {/* Live preview */}
        <div style={{ display: "grid", placeItems: "center", margin: "8px 0 16px" }}>
          <div style={{
            width: 130, height: 130, borderRadius: 16,
            background: f.color, color: "white", display: "grid",
            placeItems: "center", textAlign: "center",
            boxShadow: "0 8px 24px rgba(15,23,42,.12)",
          }}>
            <div>
              <div style={{ fontSize: 32 }}>{f.icon}</div>
              <div style={{ fontWeight: 700, marginTop: 4 }}>{f.label || "Tile name"}</div>
            </div>
          </div>
        </div>

        <div className="form-grid">
          <div className="form-row">
            <label>Label</label>
            <input className="input" value={f.label} onChange={set("label")} required/>
          </div>
          <div className="form-row">
            <label>Kind</label>
            <select className="select" value={f.kind} onChange={set("kind")}>
              <option value="payment">Payment (fee)</option>
              <option value="expense">Expense</option>
            </select>
          </div>
          {f.kind === "payment" ? (
            <div className="form-row">
              <label>Fee head (label on receipt)</label>
              <input className="input" value={f.fee_head} onChange={set("fee_head")}
                     placeholder="Tuition / Transport / …"/>
            </div>
          ) : (
            <div className="form-row">
              <label>Expense category</label>
              <select className="select" value={f.category} onChange={set("category")}>
                {EXPENSE_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
          )}
          <div className="form-row">
            <label>Sort order</label>
            <input className="input" type="number" value={f.sort_order} onChange={set("sort_order")}/>
          </div>
        </div>

        <div className="form-row">
          <label>Icon</label>
          <div className="flex" style={{ flexWrap: "wrap", gap: 6 }}>
            {ICON_PRESETS.map((i) => (
              <button type="button" key={i} className={"icon-chip" + (f.icon === i ? " on" : "")}
                      onClick={() => setF({ ...f, icon: i })}>{i}</button>
            ))}
            <input className="input" value={f.icon} onChange={set("icon")}
                   style={{ width: 80, marginLeft: 8 }}/>
          </div>
        </div>

        <div className="form-row">
          <label>Color</label>
          <div className="flex" style={{ flexWrap: "wrap", gap: 6 }}>
            {COLOR_PRESETS.map((c) => (
              <button type="button" key={c}
                      className={"color-chip" + (f.color === c ? " on" : "")}
                      style={{ background: c }}
                      onClick={() => setF({ ...f, color: c })}/>
            ))}
            <input className="input" value={f.color} onChange={set("color")}
                   style={{ width: 100, marginLeft: 8 }}/>
          </div>
        </div>

        <div className="flex gap-8" style={{ justifyContent: "flex-end", marginTop: 8 }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn" disabled={busy}>{busy ? "Saving…" : (editing ? "Save changes" : "Create tile")}</button>
        </div>
      </form>
    </div>
  );
}
