import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function StaffStudents() {
  const [classes, setClasses] = useState([]);
  const [err, setErr] = useState("");
  const [activeClass, setActiveClass] = useState(null);

  useEffect(() => {
    api.get("/students/by-class")
      .then((r) => setClasses(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);

  const totalStudents = classes.reduce((s, c) => s + c.count, 0);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Students</h1>
          <p className="page-sub">{totalStudents} students across {classes.length} class(es). Tap a class to see the roster.</p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div className="class-grid">
        {classes.map((c) => (
          <button key={c.student_class} className="class-card"
                  onClick={() => setActiveClass(c.student_class)}>
            <div className="class-card-name">Class {c.student_class}</div>
            <div className="class-card-count">{c.count}</div>
            <div className="class-card-sub">student{c.count !== 1 && "s"}</div>
          </button>
        ))}
        {classes.length === 0 && !err && (
          <div className="empty" style={{ gridColumn: "1 / -1" }}>No classes yet.</div>
        )}
      </div>

      {activeClass && (
        <ClassRosterModal
          className={activeClass}
          onClose={() => setActiveClass(null)}
        />
      )}
    </div>
  );
}

function ClassRosterModal({ className, onClose }) {
  const navigate = useNavigate();
  const [list, setList] = useState([]);
  const [q, setQ] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get(`/students/roster?student_class=${encodeURIComponent(className)}`)
      .then((r) => setList(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, [className]);

  const filtered = q.trim()
    ? list.filter((s) => s.name.toLowerCase().includes(q.toLowerCase()))
    : list;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}
           style={{ width: 540, maxHeight: "80vh", display: "flex", flexDirection: "column" }}>
        <h3 style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{
            display: "inline-grid", placeItems: "center",
            width: 36, height: 36, borderRadius: 10,
            background: "var(--brand-500)", color: "white", fontWeight: 700,
          }}>{className}</span>
          Class {className}
          <span className="text-3" style={{ fontWeight: 500, fontSize: 13 }}>· {list.length} students</span>
        </h3>

        <input
          className="input mb-16"
          placeholder="Search by name…"
          value={q}
          autoFocus
          onChange={(e) => setQ(e.target.value)}
        />

        {err && <div className="error-banner">{err}</div>}

        <div style={{ overflow: "auto", flex: 1, marginTop: -4 }}>
          {filtered.map((s) => (
            <button key={s.id} className="roster-row"
                    onClick={() => navigate(`/students/${s.id}`)}>
              <div className="avatar" style={{ background: "var(--surface-2)", color: "var(--text)" }}>
                {s.name.slice(0, 1).toUpperCase()}
              </div>
              <div style={{ flex: 1, textAlign: "left" }}>
                <div style={{ fontWeight: 600 }}>{s.name}</div>
                <div className="text-3" style={{ fontSize: 12 }}>
                  Section {s.section || "—"}
                </div>
              </div>
              <div className="text-3" style={{ fontSize: 18 }}>›</div>
            </button>
          ))}
          {filtered.length === 0 && (
            <div className="empty">No students match "{q}"</div>
          )}
        </div>

        <div className="flex" style={{ justifyContent: "flex-end", marginTop: 14 }}>
          <button className="btn btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
