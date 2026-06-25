import React, { useEffect, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { api, fmtINR } from "../api";
import { CLASS_ORDER as CLASSES } from "../school";

export default function Students() {
  const [list, setList] = useState([]);
  const [q, setQ] = useState("");
  const [cls, setCls] = useState("");
  const [err, setErr] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [importing, setImporting] = useState(false);
  const fileRef = useRef(null);

  const load = useCallback(() => {
    const params = {};
    if (q) params.q = q;
    if (cls) params.student_class = cls;
    api.get("/students", { params })
      .then((r) => setList(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, [q, cls]);

  useEffect(load, [load]);

  // Download a file (csv/xlsx) — fetch with auth then trigger save dialog
  const downloadFile = async (path, filename) => {
    try {
      const r = await api.get(path, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([r.data]));
      const a = document.createElement("a");
      a.href = url; a.download = filename; a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Download failed: " + (e?.response?.data?.detail || e.message));
    }
  };

  const onFilePicked = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";       // allow picking the same file again later
    if (!file) return;
    setImporting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/students/import", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setImportResult(r.data);
      load();
    } catch (e) {
      setImportResult({ error: e?.response?.data?.detail || e.message });
    } finally { setImporting(false); }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Students</h1>
          <p className="page-sub">{list.length} student{list.length !== 1 && "s"} · KG1 to Class 10</p>
        </div>
        <div className="flex gap-8">
          <button className="btn btn-secondary"
                  onClick={() => downloadFile("/students/template.xlsx", "students_template.xlsx")}>
            ⬇ Template
          </button>
          <button className="btn btn-secondary"
                  onClick={() => downloadFile("/students/export.xlsx", "students.xlsx")}>
            ⬇ Excel
          </button>
          <button className="btn btn-secondary"
                  onClick={() => downloadFile("/students/export.csv", "students.csv")}>
            ⬇ CSV
          </button>
          <button className="btn btn-secondary"
                  disabled={importing}
                  onClick={() => fileRef.current?.click()}>
            {importing ? "Uploading…" : "⬆ Import"}
          </button>
          <input ref={fileRef} type="file"
                 accept=".xlsx,.csv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                 style={{ display: "none" }} onChange={onFilePicked}/>
          <button className="btn" onClick={() => setShowAdd(true)}>+ Add student</button>
        </div>
      </div>

      <div className="card mb-16" style={{ padding: 14 }}>
        <div className="flex gap-12 items-center">
          <input
            className="input"
            placeholder="Search by name, admission no, or Aadhaar…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            style={{ flex: 1 }}
          />
          <select className="select" value={cls} onChange={(e) => setCls(e.target.value)} style={{ width: 160 }}>
            <option value="">All classes</option>
            {CLASSES.map((c) => <option key={c} value={c}>Class {c}</option>)}
          </select>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Adm. No.</th>
              <th>Name</th>
              <th>Class</th>
              <th>Parent</th>
              <th>Phone</th>
              <th className="num">Total fee</th>
              <th className="num">Paid</th>
              <th className="num">Due</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {list.map((s) => (
              <tr key={s.id}>
                <td>
                  <Link to={`/students/${s.id}`} style={{ fontWeight: 600 }}>
                    {s.admission_no}
                  </Link>
                </td>
                <td>{s.name}</td>
                <td>{s.student_class}{s.section ? `-${s.section}` : ""}</td>
                <td>{s.parent_name || "—"}</td>
                <td className="tabular">{s.phone || "—"}</td>
                <td className="num">{fmtINR(s.total_fee)}</td>
                <td className="num">{fmtINR(s.paid_amount)}</td>
                <td className="num">
                  <span className={"pill " + (s.due_amount > 0 ? "red" : "green")}>
                    {fmtINR(s.due_amount)}
                  </span>
                </td>
                <td>
                  <span className={"pill " + (s.status === "active" ? "green" : "")}>
                    {s.status}
                  </span>
                </td>
              </tr>
            ))}
            {list.length === 0 && (
              <tr><td colSpan={9} className="empty">No students yet. Add one to get started.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showAdd && (
        <AddStudentModal
          onClose={() => setShowAdd(false)}
          onSaved={() => { setShowAdd(false); load(); }}
        />
      )}

      {importResult && (
        <ImportResultModal result={importResult} onClose={() => setImportResult(null)}/>
      )}
    </div>
  );
}

function ImportResultModal({ result, onClose }) {
  const isErr = !!result.error;
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{isErr ? "Import failed" : "Import complete"}</h3>

        {isErr ? (
          <div className="error-banner">{result.error}</div>
        ) : (
          <>
            <div className="grid grid-cols-4" style={{ marginBottom: 14 }}>
              <div className="card stat" style={{ padding: 14 }}>
                <div className="label">Created</div>
                <div className="value green">{result.created}</div>
              </div>
              <div className="card stat" style={{ padding: 14 }}>
                <div className="label">Updated</div>
                <div className="value">{result.updated}</div>
              </div>
              <div className="card stat" style={{ padding: 14 }}>
                <div className="label">Skipped</div>
                <div className="value">{result.skipped || 0}</div>
              </div>
              <div className="card stat" style={{ padding: 14 }}>
                <div className="label">Errors</div>
                <div className={"value " + (result.error_count ? "red" : "green")}>
                  {result.error_count}
                </div>
              </div>
            </div>

            {result.errors?.length > 0 && (
              <div className="card" style={{ maxHeight: 260, overflow: "auto" }}>
                <div className="card-title">Skipped rows</div>
                <table className="table">
                  <thead><tr><th>Row #</th><th>Problem</th></tr></thead>
                  <tbody>
                    {result.errors.map((e, i) => (
                      <tr key={i}>
                        <td className="tabular">{e.row}</td>
                        <td className="text-2">{e.error}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        <div className="flex" style={{ justifyContent: "flex-end", marginTop: 14 }}>
          <button className="btn" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}

function AddStudentModal({ onClose, onSaved }) {
  const [f, setF] = useState({
    admission_no: "", name: "", student_class: "1", section: "A",
    parent_name: "", phone: "", aadhaar: "", gender: "M", last_year_dues: 0, address: "",
  });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      await api.post("/students", { ...f, last_year_dues: Number(f.last_year_dues) || 0 });
      onSaved();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to add");
    } finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={save}>
        <h3>Add new student</h3>
        {err && <div className="error-banner">{err}</div>}
        <div className="form-grid">
          <div className="form-row">
            <label>Admission no.</label>
            <input className="input" value={f.admission_no} onChange={set("admission_no")} required/>
          </div>
          <div className="form-row">
            <label>Full name</label>
            <input className="input" value={f.name} onChange={set("name")} required/>
          </div>
          <div className="form-row">
            <label>Class</label>
            <select className="select" value={f.student_class} onChange={set("student_class")}>
              {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Section</label>
            <input className="input" value={f.section} onChange={set("section")}/>
          </div>
          <div className="form-row">
            <label>Parent</label>
            <input className="input" value={f.parent_name} onChange={set("parent_name")}/>
          </div>
          <div className="form-row">
            <label>Phone</label>
            <input className="input" value={f.phone} onChange={set("phone")}/>
          </div>
          <div className="form-row">
            <label>Aadhaar</label>
            <input className="input" value={f.aadhaar} onChange={set("aadhaar")} maxLength={12}/>
          </div>
          <div className="form-row">
            <label>Gender</label>
            <select className="select" value={f.gender} onChange={set("gender")}>
              <option>M</option><option>F</option><option>O</option>
            </select>
          </div>
          <div className="form-row">
            <label>Last year dues (₹)</label>
            <input className="input" type="number" value={f.last_year_dues} onChange={set("last_year_dues")}/>
          </div>
        </div>
        <div className="form-row">
          <label>Address</label>
          <textarea className="input" rows={2} value={f.address} onChange={set("address")}/>
        </div>
        <div className="flex gap-8" style={{ justifyContent: "flex-end", marginTop: 8 }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn" disabled={busy}>{busy ? "Saving…" : "Save student"}</button>
        </div>
      </form>
    </div>
  );
}
