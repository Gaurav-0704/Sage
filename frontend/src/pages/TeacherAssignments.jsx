import React, { useEffect, useState, useCallback } from "react";
import { api, fmtDate } from "../api";
import { CLASS_ORDER as CLASSES } from "../school";

export default function TeacherAssignments() {
  const [list, setList] = useState([]);
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [classes, setClasses] = useState([]);
  const [reviewing, setReviewing] = useState(null);

  const load = useCallback(() => {
    Promise.all([
      api.get("/assignments"),
      api.get("/teacher/me/classes"),
    ]).then(([a, b]) => {
      setList(a.data); setClasses(b.data.map((c) => c.student_class));
    }).catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);
  useEffect(load, [load]);

  const remove = async (id) => {
    if (!window.confirm("Delete this assignment?")) return;
    await api.delete(`/assignments/${id}`); load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Assignments</h1>
          <p className="page-sub">{list.length} assignment(s) you've created.</p>
        </div>
        <button className="btn" onClick={() => setCreating(true)}>+ New assignment</button>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Title</th><th>Class</th><th>Subject</th>
              <th>Due</th><th className="num">Max marks</th><th></th>
            </tr>
          </thead>
          <tbody>
            {list.map((a) => (
              <tr key={a.id}>
                <td style={{ fontWeight: 500 }}>{a.title}</td>
                <td>{a.student_class}{a.section ? `-${a.section}` : ""}</td>
                <td>{a.subject}</td>
                <td>{fmtDate(a.due_date)}</td>
                <td className="num">{a.max_marks}</td>
                <td className="num">
                  <button className="btn btn-secondary"
                          style={{ padding: "5px 10px", fontSize: 12, marginRight: 6 }}
                          onClick={() => setReviewing(a)}>Submissions</button>
                  <button className="btn btn-secondary"
                          style={{ padding: "5px 10px", fontSize: 12, marginRight: 6 }}
                          onClick={() => setEditing(a)}>Edit</button>
                  <button className="btn btn-danger"
                          style={{ padding: "5px 10px", fontSize: 12 }}
                          onClick={() => remove(a.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {list.length === 0 && (
              <tr><td colSpan={6} className="empty">No assignments yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {(creating || editing) && (
        <AssignmentModal
          assignment={editing}
          classes={classes.length ? classes : CLASSES}
          onClose={() => { setEditing(null); setCreating(false); }}
          onSaved={() => { setEditing(null); setCreating(false); load(); }}
        />
      )}

      {reviewing && (
        <SubmissionsModal assignment={reviewing} onClose={() => setReviewing(null)} />
      )}
    </div>
  );
}

function SubmissionsModal({ assignment, onClose }) {
  const [subs, setSubs] = useState([]);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    api.get(`/assignments/${assignment.id}/submissions`)
      .then((r) => setSubs(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, [assignment.id]);
  useEffect(load, [load]);

  const download = async (s) => {
    try {
      const r = await api.get(`/assignments/submissions/${s.id}/file`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([r.data]));
      const a = document.createElement("a");
      a.href = url; a.download = s.file_name || "submission"; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { alert("No file or download failed"); }
  };

  const grade = async (s, marks, feedback) => {
    try {
      await api.post(`/assignments/submissions/${s.id}/grade`,
                     { marks_obtained: Number(marks), feedback: feedback || null });
      load();
    } catch (e) { alert(e?.response?.data?.detail || "Grade failed"); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}
           style={{ width: "min(820px, 96vw)", maxHeight: "92vh", overflow: "auto" }}>
        <h3>Submissions — {assignment.title} (max {assignment.max_marks})</h3>
        {err && <div className="error-banner">{err}</div>}
        {subs.length === 0 ? (
          <div className="empty">No submissions yet.</div>
        ) : (
          <table className="table">
            <thead><tr><th>Student</th><th>Answer</th><th>File</th><th>Grade</th><th></th></tr></thead>
            <tbody>
              {subs.map((s) => <GradeRow key={s.id} s={s} max={assignment.max_marks}
                                         onDownload={() => download(s)} onGrade={grade} />)}
            </tbody>
          </table>
        )}
        <div className="flex" style={{ justifyContent: "flex-end", marginTop: 12 }}>
          <button className="btn" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}

function GradeRow({ s, max, onDownload, onGrade }) {
  const [marks, setMarks] = useState(s.marks_obtained ?? "");
  const [feedback, setFeedback] = useState(s.feedback ?? "");
  return (
    <tr>
      <td style={{ fontWeight: 500 }}>{s.student_name}</td>
      <td className="text-2" style={{ maxWidth: 220, fontSize: 12 }}>{s.text || "—"}</td>
      <td>{s.file_name
        ? <button className="btn btn-secondary" style={{ padding: "3px 8px", fontSize: 11 }}
                  onClick={onDownload}>⬇ {s.file_name.slice(0, 14)}</button>
        : "—"}</td>
      <td>
        <div className="flex gap-8 items-center">
          <input type="number" min="0" max={max} value={marks}
                 onChange={(e) => setMarks(e.target.value)}
                 style={{ width: 60, padding: "4px 6px", border: "1px solid var(--border-2)", borderRadius: 6 }} />
          <span className="text-3">/ {max}</span>
        </div>
        <input className="input" placeholder="Feedback" value={feedback}
               onChange={(e) => setFeedback(e.target.value)}
               style={{ marginTop: 4, fontSize: 12, padding: "4px 6px" }} />
      </td>
      <td className="num">
        <button className="btn" style={{ padding: "4px 10px", fontSize: 12 }}
                onClick={() => onGrade(s, marks, feedback)}
                disabled={marks === ""}>
          {s.status === "graded" ? "Update" : "Grade"}
        </button>
      </td>
    </tr>
  );
}

function AssignmentModal({ assignment, classes, onClose, onSaved }) {
  const editing = !!assignment;
  const [f, setF] = useState(() => assignment ? {
    title: assignment.title || "",
    description: assignment.description || "",
    student_class: assignment.student_class || classes[0] || "1",
    section: assignment.section || "",
    subject: assignment.subject || "",
    due_date: assignment.due_date || "",
    max_marks: assignment.max_marks || 10,
  } : {
    title: "", description: "",
    student_class: classes[0] || "1",
    section: "",
    subject: "", due_date: "", max_marks: 10,
  });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const body = {
        ...f,
        max_marks: Number(f.max_marks) || 10,
        due_date: f.due_date || null,
        section: f.section || null,
        description: f.description || null,
      };
      if (editing) {
        await api.put(`/assignments/${assignment.id}`, body);
      } else {
        await api.post("/assignments", body);
      }
      onSaved();
    } catch (e) { setErr(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={save}>
        <h3>{editing ? "Edit assignment" : "New assignment"}</h3>
        {err && <div className="error-banner">{err}</div>}

        <div className="form-row">
          <label>Title</label>
          <input className="input" value={f.title} onChange={set("title")} required/>
        </div>
        <div className="form-grid">
          <div className="form-row">
            <label>Class</label>
            <select className="select" value={f.student_class} onChange={set("student_class")}>
              {classes.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Section (optional)</label>
            <input className="input" value={f.section} onChange={set("section")}
                   placeholder="A / B / blank for all"/>
          </div>
          <div className="form-row">
            <label>Subject</label>
            <input className="input" value={f.subject} onChange={set("subject")} required/>
          </div>
          <div className="form-row">
            <label>Max marks</label>
            <input className="input" type="number" value={f.max_marks} onChange={set("max_marks")}/>
          </div>
          <div className="form-row" style={{ gridColumn: "1 / -1" }}>
            <label>Due date</label>
            <input className="input" type="date" value={f.due_date} onChange={set("due_date")}/>
          </div>
        </div>
        <div className="form-row">
          <label>Description</label>
          <textarea className="input" rows={3} value={f.description} onChange={set("description")}/>
        </div>
        <div className="flex gap-8" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn" disabled={busy}>{busy ? "Saving…" : (editing ? "Save" : "Create")}</button>
        </div>
      </form>
    </div>
  );
}
