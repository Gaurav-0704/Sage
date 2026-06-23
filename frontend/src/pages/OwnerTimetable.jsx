import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api";
import { CLASS_ORDER, SUBJECTS } from "../school";
import TimetableGrid, { DAYS } from "../components/TimetableGrid";

export default function OwnerTimetable() {
  const [cls, setCls] = useState(CLASS_ORDER[0]);
  const [section, setSection] = useState("A");
  const [entries, setEntries] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    setErr("");
    api.get("/timetable", { params: { student_class: cls, section } })
      .then((r) => setEntries(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load timetable"));
  }, [cls, section]);

  useEffect(load, [load]);
  useEffect(() => {
    api.get("/teachers").then((r) => setTeachers(r.data)).catch(() => {});
  }, []);

  const removeEntry = async (id) => {
    if (!window.confirm("Remove this slot?")) return;
    await api.delete(`/timetable/${id}`); load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Timetable</h1>
          <p className="page-sub">Build the weekly schedule. Conflicts are blocked automatically.</p>
        </div>
      </div>

      <div className="card mb-16" style={{ padding: 14 }}>
        <div className="flex gap-12 items-center flex-wrap">
          <select className="select" value={cls} onChange={(e) => setCls(e.target.value)}>
            {CLASS_ORDER.map((c) => <option key={c} value={c}>Class {c}</option>)}
          </select>
          <input className="input" style={{ width: 90 }} placeholder="Section"
                 value={section} onChange={(e) => setSection(e.target.value)} />
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <TimetableGrid entries={entries} />

      <AddSlot cls={cls} section={section} teachers={teachers} onAdded={load} />

      {entries.length > 0 && (
        <div className="card mt-16" style={{ padding: 0 }}>
          <div className="card-title" style={{ padding: "12px 16px" }}>Slots</div>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Day</th><th>Period</th><th>Subject</th><th>Teacher</th><th>Room</th><th></th></tr></thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id}>
                    <td>{e.day}</td><td>P{e.period}</td><td>{e.subject}</td>
                    <td>{e.teacher_name || "—"}</td><td>{e.room || "—"}</td>
                    <td className="num">
                      <button className="btn btn-danger" style={{ padding: "4px 10px", fontSize: 12 }}
                              onClick={() => removeEntry(e.id)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function AddSlot({ cls, section, teachers, onAdded }) {
  const [f, setF] = useState({ day: "Mon", period: 1, subject: SUBJECTS[0], teacher_id: "", room: "" });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const add = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      await api.post("/timetable", {
        student_class: cls, section,
        day: f.day, period: Number(f.period), subject: f.subject,
        teacher_id: f.teacher_id ? Number(f.teacher_id) : null,
        room: f.room || null,
      });
      onAdded();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to add slot");
    } finally { setBusy(false); }
  };

  return (
    <form className="card mt-16" style={{ padding: 14 }} onSubmit={add}>
      <div className="card-title" style={{ marginBottom: 10 }}>Add slot to {cls}-{section}</div>
      {err && <div className="error-banner">{err}</div>}
      <div className="flex gap-12 items-center flex-wrap">
        <select className="select" value={f.day} onChange={set("day")}>
          {DAYS.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select className="select" value={f.period} onChange={set("period")}>
          {[1, 2, 3, 4, 5, 6, 7, 8].map((p) => <option key={p} value={p}>Period {p}</option>)}
        </select>
        <select className="select" value={f.subject} onChange={set("subject")}>
          {SUBJECTS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select className="select" value={f.teacher_id} onChange={set("teacher_id")}>
          <option value="">No teacher</option>
          {teachers.map((t) => <option key={t.id} value={t.id}>{t.name} ({t.subject || "—"})</option>)}
        </select>
        <input className="input" style={{ width: 110 }} placeholder="Room"
               value={f.room} onChange={set("room")} />
        <button className="btn" disabled={busy}>{busy ? "Adding…" : "Add"}</button>
      </div>
    </form>
  );
}
