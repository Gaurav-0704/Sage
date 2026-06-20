import React, { useEffect, useState } from "react";
import { api, API_BASE } from "../api";

/**
 * Records — Owner-only.
 *
 * Three big actions: Bonafide certificate, Transfer Certificate, and
 * Statement of Marks ("Memo"). Each opens a modal that:
 *   1. Lets the owner search and pick a student.
 *   2. Collects any extra fields the document needs (purpose for the
 *      bonafide; reason and leaving date for the TC; exam pick for
 *      the memo).
 *   3. Opens the generated certificate in a new window with the print
 *      dialog already open — pick a real printer or "Save as PDF".
 *
 * The actual document layout is on the backend (records_agent.py).
 * Keeping it server-side means a single source of truth that prints
 * identically from any browser.
 */

const ACTIONS = [
  {
    id: "bonafide",
    icon: "🎓",
    title: "Bonafide Certificate",
    sub: "Confirm a student is/was enrolled here",
    color: "#d99a5b",
  },
  {
    id: "tc",
    icon: "📄",
    title: "Transfer Certificate",
    sub: "Issue when a student leaves the school",
    color: "#c89bf5",
  },
  {
    id: "memo",
    icon: "📊",
    title: "Statement of Marks",
    sub: "Marks memo for any exam on record",
    color: "#a3d977",
  },
];

export default function OwnerRecords() {
  const [activeAction, setActiveAction] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [msg, setMsg] = useState("");

  const downloadMaster = async () => {
    try {
      const r = await api.get("/records/master.csv", { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([r.data], { type: "text/csv" }));
      const a = document.createElement("a");
      a.href = url; a.download = "students_master.csv"; a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Download failed: " + (e?.response?.data?.detail || e.message));
    }
  };

  const resync = async () => {
    setSyncing(true); setMsg("");
    try {
      await api.post("/records/sync");
      setMsg("Master archive refreshed.");
    } catch (e) {
      setMsg("Sync failed: " + (e?.response?.data?.detail || e.message));
    } finally { setSyncing(false); }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Records</h1>
          <p className="page-sub">
            Generate official documents and keep the registrar's archive up to date.
          </p>
        </div>
        <div className="flex gap-8 flex-wrap">
          <button className="btn btn-secondary" onClick={resync} disabled={syncing}>
            {syncing ? "Syncing…" : "Refresh archive"}
          </button>
          <button className="btn btn-secondary" onClick={downloadMaster}>
            ⬇ Master CSV
          </button>
        </div>
      </div>

      {msg && <div className="success-banner">{msg}</div>}

      <div className="grid grid-cols-3">
        {ACTIONS.map((a) => (
          <button key={a.id} className="game-card"
                  style={{
                    borderLeft: `4px solid ${a.color}`,
                    textAlign: "left",
                  }}
                  onClick={() => setActiveAction(a.id)}>
            <div className="icon" style={{ textAlign: "center" }}>{a.icon}</div>
            <div className="title" style={{ textAlign: "center" }}>{a.title}</div>
            <div className="sub" style={{ textAlign: "center", marginTop: 6 }}>{a.sub}</div>
          </button>
        ))}
      </div>

      <div className="card mt-24">
        <div className="card-title">How it works</div>
        <ol style={{ paddingLeft: 18, lineHeight: 1.7, color: "var(--text-2)" }}>
          <li>Pick the document you want to print from the cards above.</li>
          <li>Search for the student by name, admission number, or parent name.</li>
          <li>Fill in any document-specific fields (purpose, leaving date, etc.).</li>
          <li>The certificate opens in a new window with the print dialog ready —
              pick a real printer or "Save as PDF" from the destination dropdown.</li>
        </ol>
        <div className="text-3" style={{ fontSize: 12, marginTop: 10 }}>
          Past students (alumni / inactive) are still searchable so you can
          re-issue documents at any time.
        </div>
      </div>

      {activeAction && (
        <DocumentModal action={activeAction} onClose={() => setActiveAction(null)}/>
      )}
    </div>
  );
}


/* ---------- The picker + extra-fields modal ---------- */

function DocumentModal({ action, onClose }) {
  const [q, setQ]                 = useState("");
  const [results, setResults]     = useState([]);
  const [picked, setPicked]       = useState(null);
  const [extra, setExtra]         = useState({});
  const [exams, setExams]         = useState([]);
  const [pickedExam, setPickedExam] = useState(null);
  const [busy, setBusy]           = useState(false);
  const [err, setErr]             = useState("");

  // Live search as the owner types
  useEffect(() => {
    let alive = true;
    setBusy(true);
    api.get("/records/students", { params: { q: q || "" } })
       .then((r) => { if (alive) setResults(r.data); })
       .catch(() => {})
       .finally(() => { if (alive) setBusy(false); });
    return () => { alive = false; };
  }, [q]);

  // Once a student is picked for the memo flow, fetch their exams
  useEffect(() => {
    if (!picked || action !== "memo") return;
    api.get(`/records/students/${picked.id}/exams`)
       .then((r) => setExams(r.data))
       .catch(() => setExams([]));
  }, [picked, action]);

  const title = ACTIONS.find((a) => a.id === action)?.title || "";

  const print = async () => {
    if (!picked) return;
    if (action === "memo" && !pickedExam) {
      setErr("Pick an exam to print the memo.");
      return;
    }
    setErr("");
    let path = "";
    let params = "";
    if (action === "bonafide") {
      path = `/records/bonafide/${picked.id}`;
      const sp = new URLSearchParams();
      if (extra.purpose) sp.append("purpose", extra.purpose);
      params = sp.toString() ? "?" + sp.toString() : "";
    } else if (action === "tc") {
      path = `/records/tc/${picked.id}`;
      const sp = new URLSearchParams();
      if (extra.reason) sp.append("reason", extra.reason);
      if (extra.leaving_date) sp.append("leaving_date", extra.leaving_date);
      if (extra.last_exam_passed) sp.append("last_exam_passed", extra.last_exam_passed);
      if (extra.conduct) sp.append("conduct", extra.conduct);
      sp.append("dues_paid", extra.dues_paid === false ? "false" : "true");
      params = "?" + sp.toString();
    } else if (action === "memo") {
      path = `/records/memo/${picked.id}/${pickedExam.id}`;
    }

    // Fetch the HTML with the auth token, then write it into a new window.
    try {
      const r = await api.get(path + params, { responseType: "text" });
      const w = window.open("", "_blank", "width=820,height=900");
      if (!w) {
        alert("Popup blocked. Allow popups for " + window.location.host
              + " to see the document.");
        return;
      }
      w.document.open();
      w.document.write(r.data);
      w.document.close();
    } catch (e) {
      setErr("Couldn't generate document: " + (e?.response?.data?.detail || e.message));
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}
           style={{ width: 560, maxHeight: "90vh", display: "flex",
                     flexDirection: "column" }}>
        <h3>Print {title}</h3>

        {!picked ? (
          <>
            <div className="form-row">
              <label>Search student</label>
              <input className="input" autoFocus
                     placeholder="Name, admission number, or parent name…"
                     value={q} onChange={(e) => setQ(e.target.value)}/>
            </div>
            <div style={{ flex: 1, overflow: "auto",
                          border: "1px solid var(--border)",
                          borderRadius: 8 }}>
              {busy && results.length === 0 && (
                <div className="empty">Loading…</div>
              )}
              {results.map((s) => (
                <button key={s.id} className="roster-row"
                        onClick={() => setPicked(s)}>
                  <div className="avatar"
                        style={{ background: "var(--surface-3)", color: "var(--text)" }}>
                    {s.name.slice(0, 1).toUpperCase()}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600 }}>{s.name}</div>
                    <div className="text-3" style={{ fontSize: 12 }}>
                      Class {s.student_class}{s.section ? `-${s.section}` : ""}
                      {" · #"}{s.admission_no}
                      {s.status !== "active" && (
                        <span className="pill amber" style={{ marginLeft: 8 }}>{s.status}</span>
                      )}
                    </div>
                  </div>
                  <div className="text-3" style={{ fontSize: 18 }}>›</div>
                </button>
              ))}
              {!busy && results.length === 0 && (
                <div className="empty">No matches</div>
              )}
            </div>
          </>
        ) : (
          <>
            <div style={{ background: "var(--surface-2)", padding: 12,
                           borderRadius: 8, marginBottom: 12,
                           display: "flex", alignItems: "center", gap: 12 }}>
              <div className="avatar"
                   style={{ background: "var(--surface-3)", color: "var(--text)" }}>
                {picked.name.slice(0, 1).toUpperCase()}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{picked.name}</div>
                <div className="text-3" style={{ fontSize: 12 }}>
                  Class {picked.student_class}
                  {picked.section ? `-${picked.section}` : ""}
                  {" · "}{picked.parent_name || "—"}
                </div>
              </div>
              <button className="btn btn-secondary"
                      style={{ padding: "5px 10px", fontSize: 11 }}
                      onClick={() => { setPicked(null); setExtra({}); setPickedExam(null); }}>
                Change
              </button>
            </div>

            {action === "bonafide" && (
              <div className="form-row">
                <label>Purpose (printed on the certificate)</label>
                <input className="input"
                       placeholder="e.g. for school-bus pass / scholarship application"
                       value={extra.purpose || ""}
                       onChange={(e) => setExtra({ ...extra, purpose: e.target.value })}/>
                <div className="text-3" style={{ fontSize: 11 }}>
                  Leave blank for "whatever purpose it may be required".
                </div>
              </div>
            )}

            {action === "tc" && (
              <>
                <div className="form-grid">
                  <div className="form-row">
                    <label>Date of leaving</label>
                    <input className="input" type="date"
                           value={extra.leaving_date || ""}
                           onChange={(e) => setExtra({ ...extra, leaving_date: e.target.value })}/>
                  </div>
                  <div className="form-row">
                    <label>Conduct</label>
                    <select className="select"
                            value={extra.conduct || "Good"}
                            onChange={(e) => setExtra({ ...extra, conduct: e.target.value })}>
                      <option>Excellent</option>
                      <option>Good</option>
                      <option>Satisfactory</option>
                    </select>
                  </div>
                </div>
                <div className="form-row">
                  <label>Reason for leaving</label>
                  <input className="input"
                         placeholder="e.g. Parent's request / Family relocation"
                         value={extra.reason || ""}
                         onChange={(e) => setExtra({ ...extra, reason: e.target.value })}/>
                </div>
                <div className="form-row">
                  <label>Last examination passed (optional)</label>
                  <input className="input"
                         placeholder="e.g. Class 9 Annual Examination 2024-25"
                         value={extra.last_exam_passed || ""}
                         onChange={(e) => setExtra({ ...extra, last_exam_passed: e.target.value })}/>
                </div>
                <div className="form-row">
                  <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <input type="checkbox"
                           checked={extra.dues_paid !== false}
                           onChange={(e) => setExtra({ ...extra, dues_paid: e.target.checked })}/>
                    All school dues paid
                  </label>
                </div>
              </>
            )}

            {action === "memo" && (
              <div className="form-row">
                <label>Pick an exam ({exams.length} on record)</label>
                {exams.length === 0 ? (
                  <div className="empty" style={{ padding: 16 }}>
                    No marks recorded for this student.
                  </div>
                ) : (
                  <div style={{ maxHeight: 240, overflow: "auto",
                                 border: "1px solid var(--border)",
                                 borderRadius: 8 }}>
                    {exams.map((e) => (
                      <button key={e.id} className="roster-row"
                              onClick={() => setPickedExam(e)}
                              style={{
                                background: pickedExam?.id === e.id
                                              ? "var(--brand-50)" : "transparent",
                              }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 600 }}>{e.name}</div>
                          <div className="text-3" style={{ fontSize: 12 }}>
                            {e.academic_year} · Class {e.student_class}
                            {e.date && ` · ${e.date}`}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {err && <div className="error-banner">{err}</div>}

            <div className="flex gap-8" style={{ justifyContent: "flex-end",
                                                  marginTop: 8, flexWrap: "wrap" }}>
              <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
              <button className="btn" onClick={print}
                      disabled={action === "memo" && !pickedExam}>
                🖨 Generate &amp; Print
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
