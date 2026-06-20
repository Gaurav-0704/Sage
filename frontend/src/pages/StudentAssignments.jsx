import React, { useEffect, useState } from "react";
import { api, fmtDate } from "../api";

export default function StudentAssignments() {
  const [list, setList] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/student/me/assignments")
      .then((r) => setList(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">My Assignments</h1>
          <p className="page-sub">All assignments for your class — past and upcoming.</p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      {list.length === 0 ? (
        <div className="empty">No assignments yet.</div>
      ) : (
        <div className="grid grid-cols-2">
          {list.map((a) => {
            const overdue = a.due_date && a.due_date < today;
            return (
              <div key={a.id} className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 15 }}>{a.title}</div>
                    <div className="text-3" style={{ fontSize: 12, marginTop: 2 }}>
                      {a.subject} · {a.teacher_name || "Teacher"}
                    </div>
                  </div>
                  <span className={"pill " + (overdue ? "red" : "green")}>
                    {overdue ? "Overdue" : "Due " + fmtDate(a.due_date)}
                  </span>
                </div>
                {a.description && (
                  <div style={{ marginTop: 10, fontSize: 13, color: "var(--text-2)", lineHeight: 1.5 }}>
                    {a.description}
                  </div>
                )}
                <div className="text-3" style={{ fontSize: 11, marginTop: 12 }}>
                  Max marks: {a.max_marks}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
