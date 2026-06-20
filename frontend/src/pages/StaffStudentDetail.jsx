import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell,
  LineChart, Line, Legend,
} from "recharts";

export default function StaffStudentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [reports, setReports] = useState([]);
  const [perf, setPerf] = useState(null);
  const [tab, setTab] = useState("profile");
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([
      api.get(`/students/${id}/profile`),
      api.get(`/students/${id}/exam-reports`),
      api.get(`/students/${id}/performance`),
    ]).then(([a, b, c]) => {
      setProfile(a.data); setReports(b.data); setPerf(c.data);
    }).catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, [id]);

  if (err) return <div className="error-banner">{err}</div>;
  if (!profile) return <div className="empty">Loading…</div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <button onClick={() => navigate(-1)} className="text-2"
                  style={{ background: "none", border: 0, padding: 0, fontSize: 12, cursor: "pointer" }}>
            ← Back
          </button>
          <h1 className="page-title" style={{ marginTop: 4 }}>{profile.name}</h1>
          <p className="page-sub">
            Class {profile.student_class}{profile.section ? `-${profile.section}` : ""}
          </p>
        </div>
      </div>

      <div className="tabs">
        {[
          ["profile", "Profile"],
          ["reports", `Reports (${reports.length})`],
          ["performance", "Class Performance"],
        ].map(([k, label]) => (
          <button key={k}
                  className={"tab" + (tab === k ? " active" : "")}
                  onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>

      {tab === "profile" && <ProfilePanel p={profile}/>}
      {tab === "reports" && <ReportsPanel reports={reports}/>}
      {tab === "performance" && <PerformancePanel perf={perf}/>}
    </div>
  );
}

function ProfilePanel({ p }) {
  return (
    <div className="card">
      <div className="card-title">Profile</div>
      <Row label="Name"           value={p.name}/>
      <Row label="Class"          value={`${p.student_class}${p.section ? ` - ${p.section}` : ""}`}/>
      <Row label="Father / Guardian" value={p.parent_name || "—"}/>
      <Row label="Contact number" value={p.phone || "—"} mono/>
      <Row label="Address"        value={p.address || "—"} last/>
    </div>
  );
}

function Row({ label, value, mono, last }) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between",
      padding: "10px 0",
      borderBottom: last ? "none" : "1px solid var(--border)",
    }}>
      <div className="text-2" style={{ fontSize: 12 }}>{label}</div>
      <div style={{ fontWeight: 500, fontVariantNumeric: mono ? "tabular-nums" : "normal", maxWidth: "60%", textAlign: "right" }}>
        {value}
      </div>
    </div>
  );
}

function ReportsPanel({ reports }) {
  if (reports.length === 0) {
    return <div className="empty">No exam marks recorded yet.</div>;
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
              {r.subjects.map((s) => {
                const pct = (s.marks_obtained / s.max_marks * 100);
                return (
                  <tr key={s.id}>
                    <td>{s.subject}</td>
                    <td className="num">{s.marks_obtained}</td>
                    <td className="num">{s.max_marks}</td>
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

function PerformancePanel({ perf }) {
  if (!perf || !perf.exam_id) {
    return <div className="empty">No performance data yet — Owner needs to enter marks for the latest exam.</div>;
  }
  const data = perf.subject_breakdown.map((s) => ({
    subject: s.subject, "Student": s.student_percentage, "Class avg": s.class_average,
  }));
  return (
    <>
      <div className="card mb-16">
        <div className="card-title">{perf.exam_name} · summary</div>
        <div className="grid grid-cols-3">
          <Stat label="Student %"   value={perf.student_percentage + "%"} green={perf.student_percentage >= perf.class_average}/>
          <Stat label="Class avg"   value={perf.class_average + "%"}/>
          <Stat label="Class rank"  value={`${perf.rank} of ${perf.class_size}`}/>
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

function Stat({ label, value, green }) {
  return (
    <div className="card stat" style={{ padding: 14 }}>
      <div className="label">{label}</div>
      <div className={"value " + (green ? "green" : "")}>{value}</div>
    </div>
  );
}

function gradePill(g) {
  return ({ "A+": "green", "A": "green", "B": "indigo",
           "C": "amber", "D": "amber", "E": "red", "F": "red" }[g] || "");
}
