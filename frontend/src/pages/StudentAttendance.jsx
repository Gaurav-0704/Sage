import React, { useEffect, useState } from "react";
import { api } from "../api";

const fmtDate = (d) => {
  try {
    return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  } catch { return d; }
};

const STATUS_CLS = { present: "green", late: "amber", absent: "red", leave: "" };

export default function StudentAttendance() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/student/me/attendance")
      .then((r) => setData(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load attendance"));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">My Attendance</h1>
          <p className="page-sub">Your attendance record and percentage.</p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      {data && (
        <>
          <div className="grid grid-cols-4 mb-16">
            <div className="card stat" style={{ padding: 16 }}>
              <div className="label">Attendance</div>
              <div className={"value " + (data.percentage >= 75 ? "green" : data.percentage >= 50 ? "" : "red")}>
                {data.percentage}%
              </div>
            </div>
            <div className="card stat" style={{ padding: 16 }}>
              <div className="label">Present</div><div className="value green">{data.present + data.late}</div>
            </div>
            <div className="card stat" style={{ padding: 16 }}>
              <div className="label">Absent</div><div className="value red">{data.absent}</div>
            </div>
            <div className="card stat" style={{ padding: 16 }}>
              <div className="label">Total days</div><div className="value">{data.total}</div>
            </div>
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
                {data.records.length === 0 && (
                  <tr><td colSpan={3} className="empty">No attendance recorded yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
