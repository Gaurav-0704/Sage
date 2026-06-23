import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api";

const STATUSES = [
  { key: "present", label: "P", title: "Present", cls: "green" },
  { key: "absent",  label: "A", title: "Absent",  cls: "red" },
  { key: "late",    label: "L", title: "Late",    cls: "amber" },
  { key: "leave",   label: "Lv", title: "Leave",  cls: "" },
];

const today = () => new Date().toISOString().slice(0, 10);

/**
 * Reusable attendance marking grid. `classes` is the list of class names the
 * caller is allowed to mark (teacher: their classes; owner: all classes).
 */
export default function AttendanceSheet({ classes }) {
  const [cls, setCls] = useState(classes[0] || "");
  const [section, setSection] = useState("");
  const [date, setDate] = useState(today());
  const [period, setPeriod] = useState(0);
  const [rows, setRows] = useState([]);
  const [marks, setMarks] = useState({});   // student_id -> status
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    if (!cls) return;
    setErr(""); setMsg("");
    const params = { student_class: cls, date, period };
    if (section) params.section = section;
    api.get("/attendance/class", { params })
      .then((r) => {
        setRows(r.data);
        const m = {};
        r.data.forEach((s) => { m[s.student_id] = s.status || "present"; });
        setMarks(m);
      })
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load roster"));
  }, [cls, section, date, period]);

  useEffect(load, [load]);

  const setAll = (status) => {
    const m = {}; rows.forEach((s) => { m[s.student_id] = status; }); setMarks(m);
  };

  const save = async () => {
    setBusy(true); setErr(""); setMsg("");
    try {
      const payload = {
        student_class: cls, section: section || null, date, period,
        rows: rows.map((s) => ({ student_id: s.student_id, status: marks[s.student_id] })),
      };
      const r = await api.post("/attendance/mark", payload);
      setMsg(`Saved — ${r.data.created} new, ${r.data.updated} updated.`);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to save");
    } finally { setBusy(false); }
  };

  const present = rows.filter((s) => marks[s.student_id] === "present").length;

  return (
    <div>
      <div className="card mb-16" style={{ padding: 14 }}>
        <div className="flex gap-12 items-center flex-wrap">
          <select className="select" value={cls} onChange={(e) => setCls(e.target.value)}>
            {classes.map((c) => <option key={c} value={c}>Class {c}</option>)}
          </select>
          <input className="input" style={{ width: 90 }} placeholder="Section"
                 value={section} onChange={(e) => setSection(e.target.value)} />
          <input className="input" type="date" style={{ width: 160 }}
                 value={date} onChange={(e) => setDate(e.target.value)} />
          <select className="select" value={period} onChange={(e) => setPeriod(Number(e.target.value))}>
            <option value={0}>Whole day</option>
            {[1, 2, 3, 4, 5, 6, 7, 8].map((p) => <option key={p} value={p}>Period {p}</option>)}
          </select>
          <button className="btn btn-secondary" onClick={() => setAll("present")}>All present</button>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}
      {msg && <div className="success-banner">{msg}</div>}

      <div className="card" style={{ padding: 0 }}>
        <div className="flex items-center" style={{ justifyContent: "space-between", padding: "12px 16px" }}>
          <div className="text-2">{rows.length} students · {present} present</div>
          <button className="btn" disabled={busy || rows.length === 0} onClick={save}>
            {busy ? "Saving…" : "Save attendance"}
          </button>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Name</th><th>Section</th><th>Status</th></tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.student_id}>
                  <td style={{ fontWeight: 500 }}>{s.name}</td>
                  <td>{s.section || "—"}</td>
                  <td>
                    <div className="flex gap-8">
                      {STATUSES.map((st) => (
                        <button
                          key={st.key}
                          type="button"
                          title={st.title}
                          className={"pill " + (marks[s.student_id] === st.key ? st.cls || "active" : "")}
                          style={{
                            border: "1px solid var(--border, #ddd)", cursor: "pointer",
                            minWidth: 34, fontWeight: marks[s.student_id] === st.key ? 700 : 400,
                            opacity: marks[s.student_id] === st.key ? 1 : 0.55,
                          }}
                          onClick={() => setMarks({ ...marks, [s.student_id]: st.key })}
                        >
                          {st.label}
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td colSpan={3} className="empty">No active students for this class/section.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
