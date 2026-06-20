import React, { useEffect, useState, useCallback } from "react";
import { api, fmtINR, fmtDate } from "../api";
import { useAuth } from "../auth";
import { openReceipt } from "../receipt";

const CATEGORIES = ["salary", "utilities", "supplies", "maintenance", "transport", "other"];

export default function Expenses() {
  const { isStaff } = useAuth();
  const [list, setList] = useState([]);
  const [err, setErr] = useState("");
  const [showAdd, setShowAdd] = useState(false);

  const load = useCallback(() => {
    api.get("/expenses")
      .then((r) => setList(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);
  useEffect(load, [load]);

  const total = list.reduce((s, e) => s + e.amount, 0);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Expenses</h1>
          <p className="page-sub">{list.length} entries · total {fmtINR(total)}</p>
        </div>
        {isStaff && <button className="btn" onClick={() => setShowAdd(true)}>+ Add expense</button>}
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Date</th><th>Title</th><th>Category</th><th>Paid from</th>
              <th>Note</th><th className="num">Amount</th><th></th>
            </tr>
          </thead>
          <tbody>
            {list.map((e) => (
              <tr key={e.id}>
                <td>{fmtDate(e.date)}</td>
                <td style={{ fontWeight: 500 }}>{e.title}</td>
                <td><span className="pill indigo">{e.category}</span></td>
                <td><span className="pill">{e.paid_from}</span></td>
                <td className="text-2">{e.note || "—"}</td>
                <td className="num" style={{ fontWeight: 600, color: "var(--red)" }}>− {fmtINR(e.amount)}</td>
                <td className="num">
                  <button className="btn btn-secondary"
                          style={{ padding: "5px 10px", fontSize: 12 }}
                          onClick={() => openReceipt("expense", e.id)}
                          title="Print voucher">
                    🖨
                  </button>
                </td>
              </tr>
            ))}
            {list.length === 0 && (
              <tr><td colSpan={7} className="empty">No expenses recorded yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showAdd && (
        <AddExpenseModal onClose={() => setShowAdd(false)} onSaved={() => { setShowAdd(false); load(); }}/>
      )}
    </div>
  );
}

function AddExpenseModal({ onClose, onSaved }) {
  const [f, setF] = useState({
    title: "", amount: "", category: "supplies", paid_from: "cash",
    date: new Date().toISOString().slice(0, 10), note: "",
  });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const r = await api.post("/expenses", { ...f, amount: Number(f.amount) });
      onSaved();
      openReceipt("expense", r.data.id);   // pop the voucher
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={save}>
        <h3>Add expense</h3>
        {err && <div className="error-banner">{err}</div>}
        <div className="form-row">
          <label>Title</label>
          <input className="input" value={f.title} onChange={set("title")} required/>
        </div>
        <div className="form-grid">
          <div className="form-row">
            <label>Amount (₹)</label>
            <input className="input" type="number" value={f.amount} onChange={set("amount")} required/>
          </div>
          <div className="form-row">
            <label>Category</label>
            <select className="select" value={f.category} onChange={set("category")}>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Paid from</label>
            <select className="select" value={f.paid_from} onChange={set("paid_from")}>
              <option value="cash">Cash</option>
              <option value="bank">Bank</option>
            </select>
          </div>
          <div className="form-row">
            <label>Date</label>
            <input className="input" type="date" value={f.date} onChange={set("date")}/>
          </div>
        </div>
        <div className="form-row">
          <label>Note (optional)</label>
          <textarea className="input" rows={2} value={f.note} onChange={set("note")}/>
        </div>
        <div className="flex gap-8" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn" disabled={busy}>{busy ? "Saving…" : "Save expense"}</button>
        </div>
      </form>
    </div>
  );
}
