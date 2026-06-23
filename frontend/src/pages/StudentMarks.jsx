import React, { useEffect, useState } from "react";
import { api } from "../api";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";

export default function StudentMarks() {
  const [reports, setReports] = useState([]);
  const [perf, setPerf] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([
      api.get("/student/me/marks"),
      api.get("/student/me/performance"),
    ]).then(([a, b]) => { setReports(a.data); setPerf(b.data); })
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);

  const downloadReport = async (examId, examName) => {
    try {
      const r = await api.get(`/student/me/report-card/${examId}`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url; a.download = `report_${examName}.pdf`.replace(/\s+/g, "_"); a.click();
      URL.revokeObjectURL(url);
    } catch (e) { alert("Download failed"); }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">My Marks</h1>
          <p className="page-sub">Every exam you've taken so far.</p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      {perf?.exam_id && (
        <>
          <div className="grid grid-cols-3 mb-16">
            <div className="card stat">
              <div className="label">Latest %</div>
              <div className={"value " + (perf.student_percentage >= perf.class_average ? "green" : "")}>
                {perf.student_percentage}%
              </div>
              <div className="delta">{perf.exam_name}</div>
            </div>
            <div className="card stat">
              <div className="label">Class average</div>
              <div className="value">{perf.class_average}%</div>
            </div>
            <div className="card stat">
              <div className="label">Class rank</div>
              <div className="value">{perf.rank} <span className="text-3" style={{ fontSize: 14, fontWeight: 500 }}>of {perf.class_size}</span></div>
            </div>
          </div>

          <div className="card mb-16">
            <div className="card-title">Subject vs class average ({perf.exam_name})</div>
            <div style={{ height: 280 }}>
              <ResponsiveContainer>
                <BarChart data={perf.subject_breakdown.map((s) => ({
                  subject: s.subject, "You": s.student_percentage, "Class avg": s.class_average,
                }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#3d342b"/>
                  <XAxis dataKey="subject" fontSize={11} stroke="#8d7e6b"/>
                  <YAxis domain={[0, 100]} fontSize={11} stroke="#8d7e6b" tickFormatter={(v) => v + "%"}/>
                  <Tooltip contentStyle={{ background: "#2a2520", border: "1px solid #3d342b", borderRadius: 8 }}
                           formatter={(v) => v + "%"}/>
                  <Legend wrapperStyle={{ fontSize: 12 }}/>
                  <Bar dataKey="You"        fill="#d4a574" radius={[4,4,0,0]}/>
                  <Bar dataKey="Class avg"  fill="#5a4a3a" radius={[4,4,0,0]}/>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {reports.length === 0 ? (
        <div className="empty">No marks recorded yet.</div>
      ) : reports.map((r) => (
        <div key={r.exam_id} className="card mb-16">
          <div className="card-title flex between items-center">
            <span>
              {r.exam_name}
              <span className={"pill " + gradePill(r.grade)} style={{ marginLeft: 8 }}>{r.percentage}% · {r.grade}</span>
            </span>
            <button className="btn btn-secondary" style={{ padding: "4px 10px", fontSize: 12 }}
                    onClick={() => downloadReport(r.exam_id, r.exam_name)}>⬇ Report card</button>
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
    </div>
  );
}

function gradePill(g) {
  return ({ "A+": "green", "A": "green", "B": "indigo",
           "C": "amber", "D": "amber", "E": "red", "F": "red" }[g] || "");
}
