import React, { useState, useCallback } from "react";
import { api } from "../api";
import { CLASS_ORDER } from "../school";
import AttendanceSheet from "../components/AttendanceSheet";

const today = () => new Date().toISOString().slice(0, 10);

export default function OwnerAttendance() {
  const [tab, setTab] = useState("mark");

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Attendance</h1>
          <p className="page-sub">Mark any class or review attendance percentages.</p>
        </div>
        <div className="flex gap-8">
          <button className={"btn " + (tab === "mark" ? "" : "btn-secondary")}
                  onClick={() => setTab("mark")}>Mark</button>
          <button className={"btn " + (tab === "summary" ? "" : "btn-secondary")}
                  onClick={() => setTab("summary")}>Summary</button>
        </div>
      </div>

      {tab === "mark" ? <AttendanceSheet classes={CLASS_ORDER} /> : <Summary />}
    </div>
  );
}

function Summary() {
  const [cls, setCls] = useState(CLASS_ORDER[0]);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState(today());
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    setErr("");
    const params = { student_class: cls };
    if (start) params.start = start;
    if (end) params.end = end;
    api.get("/attendance/summary", { params })
      .then((r) => setRows(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load summary"));
  }, [cls, start, end]);

  return (
    <div>
      <div className="card mb-16" style={{ padding: 14 }}>
        <div className="flex gap-12 items-center flex-wrap">
          <select className="select" value={cls} onChange={(e) => setCls(e.target.value)}>
            {CLASS_ORDER.map((c) => <option key={c} value={c}>Class {c}</option>)}
          </select>
          <label className="text-2">From</label>
          <input className="input" type="date" style={{ width: 160 }}
                 value={start} onChange={(e) => setStart(e.target.value)} />
          <label className="text-2">To</label>
          <input className="input" type="date" style={{ width: 160 }}
                 value={end} onChange={(e) => setEnd(e.target.value)} />
          <button className="btn" onClick={load}>Load</button>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th><th>Section</th>
              <th className="num">Days</th><th className="num">Present</th>
              <th className="num">Absent</th><th className="num">Late</th>
              <th className="num">Leave</th><th className="num">%</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.student_id}>
                <td style={{ fontWeight: 500 }}>{r.name}</td>
                <td>{r.section || "—"}</td>
                <td className="num">{r.total}</td>
                <td className="num">{r.present}</td>
                <td className="num">{r.absent}</td>
                <td className="num">{r.late}</td>
                <td className="num">{r.leave}</td>
                <td className="num">
                  <span className={"pill " + (r.percentage >= 75 ? "green" : r.percentage >= 50 ? "amber" : "red")}>
                    {r.percentage}%
                  </span>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={8} className="empty">Pick a class and press Load.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
