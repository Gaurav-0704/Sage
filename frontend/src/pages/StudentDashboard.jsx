import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate } from "../api";
import CredentialsCard from "../components/CredentialsCard";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";

export default function StudentDashboard() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/student/me/dashboard")
      .then((r) => setD(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);

  if (err) return <div className="error-banner">{err}</div>;
  if (!d)  return <div className="empty">Loading…</div>;

  const trend = d.recent_marks.map((r) => ({ name: r.exam_name, percentage: r.percentage }));

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Hi, {d.name?.split(" ")[0]} 👋</h1>
          <p className="page-sub">
            Class {d.student_class}{d.section ? `-${d.section}` : ""}
          </p>
        </div>
        <span className="pill green">Student</span>
      </div>

      <CredentialsCard/>

      <div className="grid grid-cols-3 mb-16">
        <div className="card stat">
          <div className="label">Latest score</div>
          <div className="value">
            {d.recent_marks.length ? `${d.recent_marks[d.recent_marks.length - 1].percentage}%` : "—"}
          </div>
          <div className="delta">
            {d.recent_marks.length ? d.recent_marks[d.recent_marks.length - 1].exam_name : "no exams yet"}
          </div>
        </div>
        <div className="card stat">
          <div className="label">Upcoming work</div>
          <div className="value">{d.upcoming_assignments.length}</div>
          <div className="delta">assignment{d.upcoming_assignments.length !== 1 && "s"}</div>
        </div>
        <div className="card stat">
          <div className="label">Next exam</div>
          <div className="value">{d.next_exam ? d.next_exam.name : "—"}</div>
          <div className="delta">{d.next_exam ? fmtDate(d.next_exam.date) : "nothing scheduled"}</div>
        </div>
      </div>

      {trend.length >= 2 && (
        <div className="card mb-16">
          <div className="card-title">Your progress</div>
          <div style={{ height: 220 }}>
            <ResponsiveContainer>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#3d342b"/>
                <XAxis dataKey="name" fontSize={11} stroke="#8d7e6b"/>
                <YAxis domain={[0, 100]} fontSize={11} stroke="#8d7e6b" tickFormatter={(v) => v + "%"}/>
                <Tooltip contentStyle={{ background: "#2a2520", border: "1px solid #3d342b", borderRadius: 8 }}
                         formatter={(v) => v + "%"}/>
                <Line dataKey="percentage" stroke="#d4a574" strokeWidth={3} dot={{ r: 4 }}/>
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-title">
          Coming up
          <Link to="/my-assignments" style={{ fontSize: 12 }}>See all →</Link>
        </div>
        {d.upcoming_assignments.length === 0 ? (
          <div className="empty">Nothing due right now. Treat yourself to a Mind Game →</div>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Title</th><th>Subject</th><th>Due</th><th className="num">Max marks</th></tr>
            </thead>
            <tbody>
              {d.upcoming_assignments.map((a) => (
                <tr key={a.id}>
                  <td style={{ fontWeight: 500 }}>{a.title}</td>
                  <td>{a.subject}</td>
                  <td>{fmtDate(a.due_date)}</td>
                  <td className="num">{a.max_marks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
