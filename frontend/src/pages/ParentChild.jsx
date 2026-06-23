import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { api, fmtINR, fmtDate } from "../api";

const TABS = ["attendance", "marks", "fees", "assignments"];
const STATUS_CLS = { present: "green", late: "amber", absent: "red", leave: "" };

export default function ParentChild() {
  const { id } = useParams();
  const [tab, setTab] = useState("attendance");
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    setErr(""); setData(null);
    api.get(`/parent/me/children/${id}/${tab}`)
      .then((r) => setData(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, [id, tab]);
  useEffect(load, [load]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Child details</h1>
          <p className="page-sub"><Link to="/">← Back to my children</Link></p>
        </div>
        <div className="flex gap-8 flex-wrap">
          {TABS.map((t) => (
            <button key={t} className={"btn " + (tab === t ? "" : "btn-secondary")}
                    style={{ textTransform: "capitalize" }} onClick={() => setTab(t)}>{t}</button>
          ))}
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      {data && tab === "attendance" && <AttendanceView data={data} />}
      {data && tab === "marks" && <MarksView data={data} />}
      {data && tab === "fees" && <FeesView data={data} />}
      {data && tab === "assignments" && <AssignmentsView data={data} />}
    </div>
  );
}

function AttendanceView({ data }) {
  return (
    <>
      <div className="grid grid-cols-4 mb-16">
        <div className="card stat" style={{ padding: 16 }}>
          <div className="label">Attendance</div>
          <div className={"value " + (data.percentage >= 75 ? "green" : "red")}>{data.percentage}%</div>
        </div>
        <div className="card stat" style={{ padding: 16 }}><div className="label">Present</div><div className="value green">{data.present + data.late}</div></div>
        <div className="card stat" style={{ padding: 16 }}><div className="label">Absent</div><div className="value red">{data.absent}</div></div>
        <div className="card stat" style={{ padding: 16 }}><div className="label">Total days</div><div className="value">{data.total}</div></div>
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Date</th><th>Period</th><th>Status</th></tr></thead>
          <tbody>
            {data.records.map((r) => (
              <tr key={r.id}>
                <td>{fmtDate(r.date)}</td>
                <td>{r.period === 0 ? "Whole day" : `Period ${r.period}`}</td>
                <td><span className={"pill " + (STATUS_CLS[r.status] || "")}>{r.status}</span></td>
              </tr>
            ))}
            {data.records.length === 0 && <tr><td colSpan={3} className="empty">No records.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}

function MarksView({ data }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead><tr><th>Exam</th><th>Year</th><th className="num">Obtained</th><th className="num">Max</th><th className="num">%</th><th>Grade</th></tr></thead>
        <tbody>
          {data.map((r) => (
            <tr key={r.exam_id}>
              <td>{r.exam_name}</td><td>{r.academic_year}</td>
              <td className="num">{r.total_obtained}</td><td className="num">{r.total_max}</td>
              <td className="num">{r.percentage}%</td><td><span className="pill">{r.grade}</span></td>
            </tr>
          ))}
          {data.length === 0 && <tr><td colSpan={6} className="empty">No marks yet.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function FeesView({ data }) {
  return (
    <>
      <div className="grid grid-cols-3 mb-16">
        <div className="card stat" style={{ padding: 16 }}><div className="label">Total fee</div><div className="value">{fmtINR(data.total_fee)}</div></div>
        <div className="card stat" style={{ padding: 16 }}><div className="label">Paid</div><div className="value green">{fmtINR(data.paid_amount)}</div></div>
        <div className="card stat" style={{ padding: 16 }}><div className="label">Due</div><div className={"value " + (data.due_amount > 0 ? "red" : "green")}>{fmtINR(data.due_amount)}</div></div>
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Date</th><th>Mode</th><th>Head</th><th className="num">Amount</th></tr></thead>
          <tbody>
            {data.payments.map((p) => (
              <tr key={p.id}>
                <td>{fmtDate(p.date)}</td><td>{p.mode}</td><td>{p.fee_head || "—"}</td>
                <td className="num">{fmtINR(p.amount)}</td>
              </tr>
            ))}
            {data.payments.length === 0 && <tr><td colSpan={4} className="empty">No payments recorded.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}

function AssignmentsView({ data }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead><tr><th>Subject</th><th>Title</th><th>Due</th><th className="num">Max</th></tr></thead>
        <tbody>
          {data.map((a) => (
            <tr key={a.id}>
              <td>{a.subject}</td><td>{a.title}</td>
              <td>{a.due_date ? fmtDate(a.due_date) : "—"}</td><td className="num">{a.max_marks}</td>
            </tr>
          ))}
          {data.length === 0 && <tr><td colSpan={4} className="empty">No assignments.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
