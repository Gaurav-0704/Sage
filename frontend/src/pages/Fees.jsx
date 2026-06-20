import React, { useEffect, useState, useCallback } from "react";
import { api, fmtINR } from "../api";
import { useAuth } from "../auth";
import { openReceipt } from "../receipt";
import { CLASS_ORDER as CLASSES } from "../school";

export default function Fees() {
  const { isStaff } = useAuth();
  const [structures, setStructures] = useState([]);
  const [payments, setPayments] = useState([]);
  const [err, setErr] = useState("");
  const [showStruct, setShowStruct] = useState(false);

  const load = useCallback(() => {
    Promise.all([
      api.get("/fee-structures"),
      api.get("/payments"),
    ])
      .then(([a, b]) => { setStructures(a.data); setPayments(b.data); })
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);

  useEffect(load, [load]);

  const apply = async (id) => {
    try {
      const r = await api.post(`/fee-structures/${id}/apply`);
      alert(`Created ${r.data.created} fee bills for class ${r.data.class}`);
      load();
    } catch (e) { alert(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Fees</h1>
          <p className="page-sub">Per-class fee structures and recent payments</p>
        </div>
        {isStaff && (
          <button className="btn" onClick={() => setShowStruct(true)}>+ Add fee structure</button>
        )}
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div className="card mb-16">
        <div className="card-title">Fee structures</div>
        <table className="table">
          <thead>
            <tr>
              <th>Class</th><th>Year</th>
              <th className="num">Tuition</th>
              <th className="num">Transport</th>
              <th className="num">Books</th>
              <th className="num">Uniform</th>
              <th className="num">Other</th>
              <th className="num">Total</th>
              {isStaff && <th></th>}
            </tr>
          </thead>
          <tbody>
            {structures.map((s) => {
              const total = s.tuition_fee + s.transport_fee + s.books_fee + s.uniform_fee + s.other_fee;
              return (
                <tr key={s.id}>
                  <td>{s.student_class}</td>
                  <td>{s.academic_year}</td>
                  <td className="num">{fmtINR(s.tuition_fee)}</td>
                  <td className="num">{fmtINR(s.transport_fee)}</td>
                  <td className="num">{fmtINR(s.books_fee)}</td>
                  <td className="num">{fmtINR(s.uniform_fee)}</td>
                  <td className="num">{fmtINR(s.other_fee)}</td>
                  <td className="num" style={{ fontWeight: 600 }}>{fmtINR(total)}</td>
                  {isStaff && (
                    <td>
                      <button className="btn btn-secondary" style={{ padding: "6px 10px", fontSize: 12 }}
                              onClick={() => apply(s.id)}>
                        Apply to class
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
            {structures.length === 0 && (
              <tr><td colSpan={isStaff ? 9 : 8} className="empty">
                No structures yet. Create one and apply it to bill all students in that class.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="card-title">Recent payments</div>
        <table className="table">
          <thead>
            <tr><th>Date</th><th>Student #</th><th>Mode</th><th>Reference</th><th className="num">Amount</th><th></th></tr>
          </thead>
          <tbody>
            {payments.slice(0, 25).map((p) => (
              <tr key={p.id}>
                <td>{p.date}</td>
                <td>{p.student_id}</td>
                <td><span className="pill">{p.mode}</span></td>
                <td className="text-2">{p.reference || "—"}</td>
                <td className="num">{fmtINR(p.amount)}</td>
                <td className="num">
                  <button className="btn btn-secondary"
                          style={{ padding: "5px 10px", fontSize: 12 }}
                          onClick={() => openReceipt("payment", p.id)}
                          title="Print receipt">
                    🖨
                  </button>
                </td>
              </tr>
            ))}
            {payments.length === 0 && (
              <tr><td colSpan={6} className="empty">No payments recorded yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showStruct && (
        <StructureModal onClose={() => setShowStruct(false)} onSaved={() => { setShowStruct(false); load(); }}/>
      )}
    </div>
  );
}

function StructureModal({ onClose, onSaved }) {
  const [f, setF] = useState({
    student_class: "1", academic_year: "2025-26",
    tuition_fee: 0, transport_fee: 0, books_fee: 0, uniform_fee: 0, other_fee: 0,
  });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      await api.post("/fee-structures", {
        student_class: f.student_class,
        academic_year: f.academic_year,
        tuition_fee: Number(f.tuition_fee) || 0,
        transport_fee: Number(f.transport_fee) || 0,
        books_fee: Number(f.books_fee) || 0,
        uniform_fee: Number(f.uniform_fee) || 0,
        other_fee: Number(f.other_fee) || 0,
      });
      onSaved();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={save}>
        <h3>New fee structure</h3>
        {err && <div className="error-banner">{err}</div>}
        <div className="form-grid">
          <div className="form-row">
            <label>Class</label>
            <select className="select" value={f.student_class} onChange={set("student_class")}>
              {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Academic year</label>
            <input className="input" value={f.academic_year} onChange={set("academic_year")}/>
          </div>
          <div className="form-row">
            <label>Tuition (₹)</label>
            <input className="input" type="number" value={f.tuition_fee} onChange={set("tuition_fee")}/>
          </div>
          <div className="form-row">
            <label>Transport (₹)</label>
            <input className="input" type="number" value={f.transport_fee} onChange={set("transport_fee")}/>
          </div>
          <div className="form-row">
            <label>Books (₹)</label>
            <input className="input" type="number" value={f.books_fee} onChange={set("books_fee")}/>
          </div>
          <div className="form-row">
            <label>Uniform (₹)</label>
            <input className="input" type="number" value={f.uniform_fee} onChange={set("uniform_fee")}/>
          </div>
          <div className="form-row">
            <label>Other (₹)</label>
            <input className="input" type="number" value={f.other_fee} onChange={set("other_fee")}/>
          </div>
        </div>
        <div className="flex gap-8" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn" disabled={busy}>{busy ? "Saving…" : "Save structure"}</button>
        </div>
      </form>
    </div>
  );
}
