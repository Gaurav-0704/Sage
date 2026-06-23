import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api";
import { CLASS_ORDER as CLASSES, SUBJECTS } from "../school";

export default function Marks() {
  const [exams, setExams] = useState([]);
  const [filterClass, setFilterClass] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [activeExam, setActiveExam] = useState(null);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    const url = "/exams" + (filterClass ? `?student_class=${filterClass}` : "");
    api.get(url).then((r) => setExams(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, [filterClass]);
  useEffect(load, [load]);

  const remove = async (id) => {
    if (!window.confirm("Delete this exam (and all its marks)?")) return;
    await api.delete(`/exams/${id}`);
    load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Marks & Exams</h1>
          <p className="page-sub">Define exams per class, then enter marks in a grid.</p>
        </div>
        <button className="btn" onClick={() => setShowCreate(true)}>+ New exam</button>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div className="card mb-16" style={{ padding: 14 }}>
        <div className="flex gap-12 items-center">
          <span className="text-2" style={{ fontSize: 12, fontWeight: 600 }}>Filter</span>
          <select className="select" value={filterClass} onChange={(e) => setFilterClass(e.target.value)}
                  style={{ width: 180 }}>
            <option value="">All classes</option>
            {CLASSES.map((c) => <option key={c} value={c}>Class {c}</option>)}
          </select>
        </div>
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Exam</th><th>Class</th><th>Year</th><th>Date</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {exams.map((e) => (
              <tr key={e.id}>
                <td style={{ fontWeight: 600 }}>{e.name}</td>
                <td>{e.student_class}</td>
                <td>{e.academic_year}</td>
                <td>{e.date || "—"}</td>
                <td className="num">
                  <button className="btn btn-secondary"
                          style={{ padding: "6px 10px", fontSize: 12, marginRight: 6 }}
                          onClick={() => setActiveExam(e)}>Enter marks</button>
                  <button className="btn btn-danger"
                          style={{ padding: "6px 10px", fontSize: 12 }}
                          onClick={() => remove(e.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {exams.length === 0 && (
              <tr><td colSpan={5} className="empty">No exams yet — create one to start entering marks.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <CreateExamModal onClose={() => setShowCreate(false)}
                         onSaved={() => { setShowCreate(false); load(); }}/>
      )}

      {activeExam && (
        <MarksGridModal exam={activeExam}
                        onClose={() => setActiveExam(null)}/>
      )}
    </div>
  );
}

function CreateExamModal({ onClose, onSaved }) {
  const [f, setF] = useState({
    name: "Term 1", student_class: "1", academic_year: "2025-26",
    date: new Date().toISOString().slice(0, 10),
  });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const save = async (ev) => {
    ev.preventDefault(); setErr(""); setBusy(true);
    try {
      await api.post("/exams", f);
      onSaved();
    } catch (e) { setErr(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={save}>
        <h3>New exam</h3>
        {err && <div className="error-banner">{err}</div>}
        <div className="form-grid">
          <div className="form-row">
            <label>Exam name</label>
            <input className="input" value={f.name} onChange={set("name")} required/>
          </div>
          <div className="form-row">
            <label>Class</label>
            <select className="select" value={f.student_class} onChange={set("student_class")}>
              {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Academic year</label>
            <input className="input" value={f.academic_year} onChange={set("academic_year")}/>
          </div>
          <div className="form-row">
            <label>Date</label>
            <input className="input" type="date" value={f.date} onChange={set("date")}/>
          </div>
        </div>
        <div className="flex gap-8" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn" disabled={busy}>{busy ? "Saving…" : "Create exam"}</button>
        </div>
      </form>
    </div>
  );
}

function MarksGridModal({ exam, onClose }) {
  const [students, setStudents] = useState([]);
  const [marks, setMarks] = useState({}); // {`${student_id}.${subject}`: number}
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get(`/students/roster?student_class=${encodeURIComponent(exam.student_class)}`),
      api.get(`/exams/${exam.id}/marks`),
    ]).then(([rs, ms]) => {
      setStudents(rs.data);
      const map = {};
      ms.data.forEach((m) => { map[`${m.student_id}.${m.subject}`] = m.marks_obtained; });
      setMarks(map);
    }).catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, [exam.id, exam.student_class]);

  const setCell = (sid, subj, v) => {
    setMarks({ ...marks, [`${sid}.${subj}`]: v });
    setSaved(false);
  };

  const downloadReport = async (sid, name) => {
    try {
      const r = await api.get(`/exams/${exam.id}/report-card/${sid}`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url; a.download = `report_${name}_${exam.name}.pdf`.replace(/\s+/g, "_"); a.click();
      URL.revokeObjectURL(url);
    } catch (e) { alert("Download failed — save marks first."); }
  };

  const save = async () => {
    setErr(""); setBusy(true); setSaved(false);
    const rows = [];
    students.forEach((s) => {
      SUBJECTS.forEach((subj) => {
        const v = marks[`${s.id}.${subj}`];
        if (v !== undefined && v !== "") {
          const n = Number(v);
          if (!Number.isNaN(n)) rows.push({ student_id: s.id, subject: subj, marks_obtained: n, max_marks: 100 });
        }
      });
    });
    try {
      await api.post(`/exams/${exam.id}/marks/bulk`, { exam_id: exam.id, rows });
      setSaved(true);
    } catch (e) { setErr(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}
           style={{ width: "min(900px, 96vw)", maxHeight: "92vh", display: "flex", flexDirection: "column" }}>
        <h3>{exam.name} — Class {exam.student_class}</h3>
        {err && <div className="error-banner">{err}</div>}
        {saved && <div style={{ padding: 10, background: "var(--green-bg)", color: "var(--green)", borderRadius: 8, marginBottom: 12, fontSize: 13 }}>Marks saved.</div>}

        <div style={{ overflow: "auto", flex: 1, border: "1px solid var(--border)", borderRadius: 8 }}>
          <table className="table" style={{ minWidth: 720 }}>
            <thead>
              <tr>
                <th style={{ position: "sticky", left: 0, background: "var(--surface-2)", zIndex: 1 }}>Student</th>
                {SUBJECTS.map((s) => <th key={s} className="num">{s}</th>)}
                <th className="num">Total</th>
                <th className="num">Report</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => {
                const total = SUBJECTS.reduce((sum, subj) => {
                  const v = Number(marks[`${s.id}.${subj}`] || 0);
                  return sum + (Number.isNaN(v) ? 0 : v);
                }, 0);
                return (
                  <tr key={s.id}>
                    <td style={{ position: "sticky", left: 0, background: "var(--surface)", fontWeight: 500 }}>
                      {s.name} <span className="text-3" style={{ fontSize: 11 }}>({s.section})</span>
                    </td>
                    {SUBJECTS.map((subj) => (
                      <td key={subj} className="num" style={{ padding: 4 }}>
                        <input
                          type="number" inputMode="numeric" min="0" max="100"
                          value={marks[`${s.id}.${subj}`] ?? ""}
                          onChange={(e) => setCell(s.id, subj, e.target.value)}
                          style={{ width: 72, padding: "4px 6px", border: "1px solid var(--border-2)",
                                   borderRadius: 6, textAlign: "right", fontVariantNumeric: "tabular-nums" }}
                        />
                      </td>
                    ))}
                    <td className="num" style={{ fontWeight: 600 }}>{total || "—"}</td>
                    <td className="num">
                      <button className="btn btn-secondary" style={{ padding: "3px 8px", fontSize: 11 }}
                              onClick={() => downloadReport(s.id, s.name)}>⬇ PDF</button>
                    </td>
                  </tr>
                );
              })}
              {students.length === 0 && (
                <tr><td colSpan={SUBJECTS.length + 3} className="empty">No students in this class.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex gap-8" style={{ justifyContent: "flex-end", marginTop: 12 }}>
          <button className="btn btn-secondary" onClick={onClose}>Close</button>
          <button className="btn" onClick={save} disabled={busy}>{busy ? "Saving…" : "Save all marks"}</button>
        </div>
      </div>
    </div>
  );
}
