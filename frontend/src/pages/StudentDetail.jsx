import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { api, fmtINR, fmtDate } from "../api";
import { openReceipt } from "../receipt";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  LineChart, Line, Legend,
} from "recharts";

export default function StudentDetail() {
  const { id } = useParams();
  const [s, setS] = useState(null);
  const [reports, setReports] = useState([]);
  const [perf, setPerf] = useState(null);
  const [err, setErr] = useState("");
  const [showPay, setShowPay] = useState(false);
  const [tab, setTab] = useState("profile");

  const load = useCallback(() => {
    Promise.all([
      api.get(`/students/${id}`),
      api.get(`/students/${id}/exam-reports`),
      api.get(`/students/${id}/performance`),
    ]).then(([a, b, c]) => {
      setS(a.data); setReports(b.data); setPerf(c.data);
    }).catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, [id]);

  useEffect(load, [load]);

  if (err) return <div className="error-banner">{err}</div>;
  if (!s) return <div className="empty">Loading…</div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/students" className="text-2" style={{ fontSize: 12 }}>← All students</Link>
          <h1 className="page-title" style={{ marginTop: 4 }}>{s.name}</h1>
          <p className="page-sub">
            Admission #{s.admission_no} · Class {s.student_class}{s.section ? `-${s.section}` : ""} ·
            <span className={"pill " + (s.status === "active" ? "green" : "") } style={{ marginLeft: 8 }}>
              {s.status}
            </span>
          </p>
        </div>
        <button className="btn" onClick={() => setShowPay(true)}>+ Record payment</button>
      </div>

      <div className="grid grid-cols-3 mb-16">
        <div className="card stat">
          <div className="label">Total fee</div>
          <div className="value">{fmtINR(s.total_fee)}</div>
          <div className="delta">incl. last-year dues {fmtINR(s.last_year_dues)}</div>
        </div>
        <div className="card stat">
          <div className="label">Paid so far</div>
          <div className="value green">{fmtINR(s.paid_amount)}</div>
        </div>
        <div className="card stat">
          <div className="label">Outstanding</div>
          <div className={"value " + (s.due_amount > 0 ? "red" : "green")}>
            {fmtINR(s.due_amount)}
          </div>
        </div>
      </div>

      <div className="tabs">
        {[
          ["profile",  "Profile"],
          ["payments", `Payments (${(s.payments || []).length})`],
          ["reports",  `Reports (${reports.length})`],
          ["perf",     "Class Performance"],
        ].map(([k, label]) => (
          <button key={k}
                  className={"tab" + (tab === k ? " active" : "")}
                  onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>

      {tab === "profile"  && <ProfileTab s={s}/>}
      {tab === "payments" && <PaymentsTab payments={s.payments || []}/>}
      {tab === "reports"  && <ReportsTab reports={reports}/>}
      {tab === "perf"     && <PerformanceTab perf={perf}/>}

      {showPay && (
        <PaymentModal
          studentId={s.id}
          onClose={() => setShowPay(false)}
          onSaved={() => { setShowPay(false); load(); }}
        />
      )}
    </div>
  );
}

function ProfileTab({ s }) {
  return (
    <div className="grid grid-cols-2">
      <div className="card">
        <div className="card-title">Personal details</div>
        <Detail label="Aadhaar" value={s.aadhaar || "—"} mono/>
        <Detail label="Date of birth" value={fmtDate(s.dob)}/>
        <Detail label="Gender" value={s.gender || "—"}/>
        <Detail label="Admitted on" value={fmtDate(s.admission_date)}/>
      </div>
      <div className="card">
        <div className="card-title">Contact</div>
        <Detail label="Parent / guardian" value={s.parent_name || "—"}/>
        <Detail label="Phone" value={s.phone || "—"} mono/>
        <Detail label="Address" value={s.address || "—"}/>
      </div>
    </div>
  );
}

function PaymentsTab({ payments }) {
  if (payments.length === 0) {
    return <div className="card empty">No payments recorded yet.</div>;
  }
  return (
    <div className="card">
      <div className="card-title">Payment history</div>
      <table className="table">
        <thead>
          <tr><th>Date</th><th>Mode</th><th>Fee head</th><th>Reference</th><th>Note</th><th className="num">Amount</th><th></th></tr>
        </thead>
        <tbody>
          {payments.slice().sort((a, b) => b.id - a.id).map((p) => (
            <tr key={p.id}>
              <td>{fmtDate(p.date)}</td>
              <td><span className="pill">{p.mode}</span></td>
              <td>{p.fee_head || "—"}</td>
              <td className="text-2">{p.reference || "—"}</td>
              <td className="text-2">{p.note || "—"}</td>
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
        </tbody>
      </table>
    </div>
  );
}

function ReportsTab({ reports }) {
  if (reports.length === 0) {
    return <div className="card empty">No exam marks recorded yet. Use the <strong>Marks &amp; Exams</strong> page to add them.</div>;
  }
  const trend = reports.map((r) => ({ name: r.exam_name, percentage: r.percentage }));
  return (
    <>
      {reports.length >= 2 && (
        <div className="card mb-16">
          <div className="card-title">Progress trend</div>
          <div style={{ height: 220 }}>
            <ResponsiveContainer>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e6e8ee"/>
                <XAxis dataKey="name" fontSize={11} stroke="#94a3b8"/>
                <YAxis domain={[0, 100]} fontSize={11} stroke="#94a3b8" tickFormatter={(v) => v + "%"}/>
                <Tooltip formatter={(v) => v + "%"}/>
                <Line dataKey="percentage" stroke="#2f6bff" strokeWidth={3} dot={{ r: 4 }}/>
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {reports.map((r) => (
        <div key={r.exam_id} className="card mb-16">
          <div className="card-title">
            {r.exam_name} <span className="text-3" style={{ fontWeight: 500 }}>· {r.academic_year}</span>
            <span style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span className="text-3" style={{ fontWeight: 500 }}>
                {r.total_obtained}/{r.total_max}
              </span>
              <span className={"pill " + gradePill(r.grade)}>
                {r.percentage}% · {r.grade}
              </span>
            </span>
          </div>
          <table className="table">
            <thead>
              <tr><th>Subject</th><th className="num">Obtained</th><th className="num">Max</th><th className="num">%</th></tr>
            </thead>
            <tbody>
              {r.subjects.map((sub) => {
                const pct = (sub.marks_obtained / sub.max_marks * 100);
                return (
                  <tr key={sub.id}>
                    <td>{sub.subject}</td>
                    <td className="num">{sub.marks_obtained}</td>
                    <td className="num">{sub.max_marks}</td>
                    <td className="num"
                        style={{ fontWeight: 600, color: pct >= 60 ? "var(--green)" : "var(--red)" }}>
                      {pct.toFixed(1)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </>
  );
}

function PerformanceTab({ perf }) {
  if (!perf || !perf.exam_id) {
    return <div className="card empty">No performance data yet — enter marks for the latest exam first.</div>;
  }
  const data = perf.subject_breakdown.map((s) => ({
    subject: s.subject, "Student": s.student_percentage, "Class avg": s.class_average,
  }));
  return (
    <>
      <div className="card mb-16">
        <div className="card-title">{perf.exam_name} · summary</div>
        <div className="grid grid-cols-3">
          <div className="card stat" style={{ padding: 14 }}>
            <div className="label">Student %</div>
            <div className={"value " + (perf.student_percentage >= perf.class_average ? "green" : "")}>
              {perf.student_percentage}%
            </div>
          </div>
          <div className="card stat" style={{ padding: 14 }}>
            <div className="label">Class average</div>
            <div className="value">{perf.class_average}%</div>
          </div>
          <div className="card stat" style={{ padding: 14 }}>
            <div className="label">Class rank</div>
            <div className="value">{perf.rank} of {perf.class_size}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Subject-wise comparison</div>
        <div style={{ height: 280 }}>
          <ResponsiveContainer>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e6e8ee"/>
              <XAxis dataKey="subject" fontSize={11} stroke="#94a3b8"/>
              <YAxis domain={[0, 100]} fontSize={11} stroke="#94a3b8" tickFormatter={(v) => v + "%"}/>
              <Tooltip formatter={(v) => v + "%"}/>
              <Legend wrapperStyle={{ fontSize: 12 }}/>
              <Bar dataKey="Student"   fill="#2f6bff" radius={[4,4,0,0]}/>
              <Bar dataKey="Class avg" fill="#cbd5e1" radius={[4,4,0,0]}/>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  );
}

function gradePill(g) {
  return ({ "A+": "green", "A": "green", "B": "indigo",
           "C": "amber", "D": "amber", "E": "red", "F": "red" }[g] || "");
}

function Detail({ label, value, mono }) {
  return (
    <div className="flex between" style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
      <div className="text-2" style={{ fontSize: 12 }}>{label}</div>
      <div style={{ fontWeight: 500, fontVariantNumeric: mono ? "tabular-nums" : "normal" }}>{value}</div>
    </div>
  );
}

function PaymentModal({ studentId, onClose, onSaved }) {
  const [f, setF] = useState({
    amount: "", mode: "cash",
    date: new Date().toISOString().slice(0, 10),
    reference: "", note: "",
  });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      await api.post("/payments", {
        student_id: studentId,
        amount: Number(f.amount),
        mode: f.mode,
        date: f.date,
        reference: f.reference || null,
        note: f.note || null,
      });
      onSaved();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to save");
    } finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={save}>
        <h3>Record payment</h3>
        {err && <div className="error-banner">{err}</div>}
        <div className="form-grid">
          <div className="form-row">
            <label>Amount (₹)</label>
            <input className="input" type="number" value={f.amount} onChange={set("amount")} required/>
          </div>
          <div className="form-row">
            <label>Mode</label>
            <select className="select" value={f.mode} onChange={set("mode")}>
              <option value="cash">Cash</option>
              <option value="bank">Bank</option>
            </select>
          </div>
          <div className="form-row">
            <label>Date</label>
            <input className="input" type="date" value={f.date} onChange={set("date")}/>
          </div>
          <div className="form-row">
            <label>Reference (optional)</label>
            <input className="input" value={f.reference} onChange={set("reference")} placeholder="UTR / cheque #"/>
          </div>
        </div>
        <div className="form-row">
          <label>Note</label>
          <textarea className="input" rows={2} value={f.note} onChange={set("note")}/>
        </div>
        <div className="flex gap-8" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn" disabled={busy}>{busy ? "Saving…" : "Record payment"}</button>
        </div>
      </form>
    </div>
  );
}
