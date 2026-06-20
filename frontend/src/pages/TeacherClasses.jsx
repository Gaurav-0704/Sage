import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function TeacherClasses() {
  const [classes, setClasses] = useState([]);
  const [active, setActive] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/teacher/me/classes")
      .then((r) => setClasses(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">My Classes</h1>
          <p className="page-sub">{classes.length} class(es) you teach.</p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div className="class-grid">
        {classes.map((c) => (
          <button key={c.student_class} className="class-card"
                  onClick={() => setActive(c.student_class)}>
            <div className="class-card-name">Class {c.student_class}</div>
            <div className="class-card-count">{c.count}</div>
            <div className="class-card-sub">student{c.count !== 1 && "s"}</div>
          </button>
        ))}
        {classes.length === 0 && !err && (
          <div className="empty" style={{ gridColumn: "1 / -1" }}>
            You haven't been assigned to any classes yet — ask the Owner to update your profile.
          </div>
        )}
      </div>

      {active && <ClassModal cls={active} onClose={() => setActive(null)}/>}
    </div>
  );
}

function ClassModal({ cls, onClose }) {
  const [list, setList] = useState([]);
  const [q, setQ] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get(`/teacher/me/students/${encodeURIComponent(cls)}`)
      .then((r) => setList(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed"));
  }, [cls]);

  const filtered = q.trim()
    ? list.filter((s) => s.name.toLowerCase().includes(q.toLowerCase()))
    : list;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}
           style={{ width: 520, maxHeight: "82vh", display: "flex", flexDirection: "column" }}>
        <h3>Class {cls} · {list.length} students</h3>
        <input className="input mb-16" placeholder="Search by name…"
               value={q} autoFocus onChange={(e) => setQ(e.target.value)}/>
        {err && <div className="error-banner">{err}</div>}
        <div style={{ overflow: "auto", flex: 1 }}>
          {filtered.map((s) => (
            <div key={s.id} className="roster-row" style={{ cursor: "default" }}>
              <div className="avatar" style={{ background: "var(--surface-3)", color: "var(--text)" }}>
                {s.name.slice(0, 1).toUpperCase()}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{s.name}</div>
                <div className="text-3" style={{ fontSize: 12 }}>Section {s.section || "—"}</div>
              </div>
            </div>
          ))}
          {filtered.length === 0 && <div className="empty">No matches</div>}
        </div>
        <div className="flex" style={{ justifyContent: "flex-end", marginTop: 14 }}>
          <button className="btn btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
