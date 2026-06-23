import React, { useEffect, useState, useCallback } from "react";
import { api, fmtDate } from "../api";

export default function StudentAssignments() {
  const [list, setList] = useState([]);
  const [subs, setSubs] = useState({});   // assignment_id -> submission
  const [err, setErr] = useState("");
  const [active, setActive] = useState(null);

  const load = useCallback(() => {
    Promise.all([
      api.get("/student/me/assignments"),
      api.get("/student/me/submissions"),
    ]).then(([a, b]) => {
      setList(a.data);
      const m = {}; b.data.forEach((s) => { m[s.assignment_id] = s; }); setSubs(m);
    }).catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);
  useEffect(load, [load]);

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">My Assignments</h1>
          <p className="page-sub">Submit your work and see grades + feedback.</p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      {list.length === 0 ? (
        <div className="empty">No assignments yet.</div>
      ) : (
        <div className="grid grid-cols-2">
          {list.map((a) => {
            const overdue = a.due_date && a.due_date < today;
            const sub = subs[a.id];
            return (
              <div key={a.id} className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 15 }}>{a.title}</div>
                    <div className="text-3" style={{ fontSize: 12, marginTop: 2 }}>
                      {a.subject} · {a.teacher_name || "Teacher"}
                    </div>
                  </div>
                  <span className={"pill " + (overdue && !sub ? "red" : "green")}>
                    {overdue ? "Overdue" : "Due " + fmtDate(a.due_date)}
                  </span>
                </div>
                {a.description && (
                  <div style={{ marginTop: 10, fontSize: 13, color: "var(--text-2)", lineHeight: 1.5 }}>
                    {a.description}
                  </div>
                )}

                <div className="flex between items-center" style={{ marginTop: 12 }}>
                  <span className="text-3" style={{ fontSize: 11 }}>Max marks: {a.max_marks}</span>
                  {sub ? (
                    sub.status === "graded" ? (
                      <span className="pill green">Graded: {sub.marks_obtained}/{a.max_marks}</span>
                    ) : (
                      <span className="pill amber">Submitted</span>
                    )
                  ) : (
                    <button className="btn" style={{ padding: "4px 12px", fontSize: 12 }}
                            onClick={() => setActive(a)}>Submit</button>
                  )}
                </div>

                {sub && sub.status !== "graded" && (
                  <button className="btn btn-secondary" style={{ marginTop: 8, padding: "4px 12px", fontSize: 12 }}
                          onClick={() => setActive(a)}>Edit submission</button>
                )}
                {sub && sub.feedback && (
                  <div className="text-2" style={{ marginTop: 8, fontSize: 12 }}>
                    <b>Feedback:</b> {sub.feedback}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {active && (
        <SubmitModal assignment={active} existing={subs[active.id]}
                     onClose={() => setActive(null)}
                     onSaved={() => { setActive(null); load(); }} />
      )}
    </div>
  );
}

function SubmitModal({ assignment, existing, onClose, onSaved }) {
  const [text, setText] = useState(existing?.text || "");
  const [file, setFile] = useState(null);
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const fd = new FormData();
      if (text) fd.append("text", text);
      if (file) fd.append("file", file);
      await api.post(`/student/me/assignments/${assignment.id}/submit`, fd,
                     { headers: { "Content-Type": "multipart/form-data" } });
      onSaved();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Submission failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <h3>Submit — {assignment.title}</h3>
        {err && <div className="error-banner">{err}</div>}
        <div className="form-row">
          <label>Your answer / notes</label>
          <textarea className="input" rows={5} value={text}
                    onChange={(e) => setText(e.target.value)} />
        </div>
        <div className="form-row">
          <label>Attach a file (optional, max 10 MB)</label>
          <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          {existing?.file_name && <div className="text-3" style={{ fontSize: 11 }}>Current: {existing.file_name}</div>}
        </div>
        <div className="flex gap-8" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn" disabled={busy}>{busy ? "Submitting…" : "Submit"}</button>
        </div>
      </form>
    </div>
  );
}
