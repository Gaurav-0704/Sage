import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { openReceipt } from "../receipt";
import CredentialsCard from "../components/CredentialsCard";

export default function StaffDashboard() {
  const { user } = useAuth();
  const [tiles, setTiles] = useState([]);
  const [roster, setRoster] = useState([]);
  const [active, setActive] = useState(null); // tile being entered
  const [err, setErr] = useState("");
  const [todayCount, setTodayCount] = useState(0);

  const load = useCallback(() => {
    Promise.all([api.get("/tiles"), api.get("/students/roster")])
      .then(([t, r]) => { setTiles(t.data); setRoster(r.data); })
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);
  useEffect(load, [load]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Quick Entry</h1>
          <p className="page-sub">
            Welcome, {user?.name?.split(" ")[0]}. Tap any tile to record a payment or expense.
          </p>
        </div>
        <span className="pill green">Staff</span>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <CredentialsCard/>

      <div className="tile-grid">
        {tiles.map((t) => (
          <button
            key={t.id}
            className="tile"
            style={{ "--tile-color": t.color }}
            onClick={() => setActive(t)}
          >
            <div className="tile-icon">{t.icon}</div>
            <div className="tile-label">{t.label}</div>
            <div className="tile-tag">
              {t.kind === "payment" ? "Fee" : "Expense"}
            </div>
          </button>
        ))}
        {tiles.length === 0 && (
          <div className="empty" style={{ gridColumn: "1 / -1" }}>
            No tiles configured yet. Ask the Owner to set them up in <strong>Quick Tiles</strong>.
          </div>
        )}
      </div>

      {todayCount > 0 && (
        <div className="card mt-24" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div className="text-2" style={{ fontSize: 12, fontWeight: 600 }}>Recorded today</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{todayCount} entries</div>
          </div>
          <div className="text-3" style={{ fontSize: 12 }}>Counter resets when you sign out.</div>
        </div>
      )}

      {active && (
        <EntryModal
          tile={active}
          roster={roster}
          onClose={() => setActive(null)}
          onSaved={() => { setActive(null); setTodayCount((n) => n + 1); }}
        />
      )}
    </div>
  );
}

function EntryModal({ tile, roster, onClose, onSaved }) {
  const isPay = tile.kind === "payment";
  const [studentId, setStudentId] = useState("");
  const [studentSearch, setStudentSearch] = useState("");
  const [amount, setAmount] = useState("");
  const [mode, setMode] = useState("cash");
  const [note, setNote] = useState("");
  const [reference, setReference] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const filtered = studentSearch.trim()
    ? roster.filter((s) =>
        s.name.toLowerCase().includes(studentSearch.toLowerCase()))
    : roster;

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const today = new Date().toISOString().slice(0, 10);
      if (isPay) {
        if (!studentId) throw new Error("Pick a student first");
        const res = await api.post("/payments", {
          student_id: Number(studentId),
          amount: Number(amount),
          mode, fee_head: tile.fee_head || tile.label,
          reference: reference || null,
          note: note || null,
          date: today,
        });
        // Pop the receipt
        await openReceipt(res.data.id);
      } else {
        const r = await api.post("/expenses", {
          title: note || tile.label,
          amount: Number(amount),
          category: tile.category || "other",
          paid_from: mode,
          date: today,
          note: note || null,
        });
        // Voucher pop-up matches the payment-receipt experience.
        await openReceipt("expense", r.data.id);
      }
      onSaved();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message || "Failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={submit} style={{ width: 520 }}>
        <h3 style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{
            display: "inline-grid", placeItems: "center",
            width: 36, height: 36, borderRadius: 10,
            background: tile.color, color: "white", fontSize: 18,
          }}>{tile.icon}</span>
          {isPay ? "Record fee:" : "Record expense:"} {tile.label}
        </h3>

        {err && <div className="error-banner">{err}</div>}

        {isPay && (
          <>
            <div className="form-row">
              <label>Search student</label>
              <input
                className="input"
                placeholder="Name or admission no…"
                value={studentSearch}
                onChange={(e) => setStudentSearch(e.target.value)}
              />
            </div>
            <div className="form-row">
              <label>Student ({filtered.length} match{filtered.length !== 1 && "es"})</label>
              <select
                className="select"
                size={Math.min(6, Math.max(3, filtered.length))}
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                style={{ height: "auto", padding: 4 }}
                required
              >
                {filtered.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} — Class {s.student_class}{s.section ? `-${s.section}` : ""}
                  </option>
                ))}
              </select>
            </div>
          </>
        )}

        <div className="form-grid">
          <div className="form-row">
            <label>Amount (₹)</label>
            <input
              className="input"
              type="number" inputMode="numeric"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              autoFocus={!isPay}
              required
            />
          </div>
          <div className="form-row">
            <label>{isPay ? "Mode" : "Paid from"}</label>
            <select className="select" value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="cash">💵 Cash</option>
              <option value="bank">🏦 Bank / Card</option>
            </select>
          </div>
        </div>

        {isPay && (
          <div className="form-row">
            <label>Reference (optional)</label>
            <input className="input" value={reference} onChange={(e) => setReference(e.target.value)}
                   placeholder="Cheque / UTR / transaction ID"/>
          </div>
        )}
        <div className="form-row">
          <label>Note {!isPay && "(used as expense title if blank)"}</label>
          <input className="input" value={note} onChange={(e) => setNote(e.target.value)}/>
        </div>

        <div className="flex gap-8" style={{ justifyContent: "flex-end", marginTop: 8 }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn" disabled={busy}>
            {busy ? "Saving…" : (isPay ? "Save & print receipt" : "Save expense")}
          </button>
        </div>
      </form>
    </div>
  );
}
