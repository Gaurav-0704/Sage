import React, { useEffect, useState, useCallback, useRef } from "react";
import { api } from "../api";

export default function OwnerTeachers() {
  const [list, setList] = useState([]);
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const fileRef = useRef(null);

  const load = useCallback(() => {
    api.get("/teachers")
      .then((r) => setList(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);
  useEffect(load, [load]);

  const downloadCsv = async (path, filename) => {
    try {
      const r = await api.get(path, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([r.data], { type: "text/csv" }));
      const a = document.createElement("a");
      a.href = url; a.download = filename; a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Download failed: " + (e?.response?.data?.detail || e.message));
    }
  };

  const onFilePicked = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setImporting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/teachers/import", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setImportResult(r.data);
      load();
    } catch (e) {
      setImportResult({ error: e?.response?.data?.detail || e.message });
    } finally { setImporting(false); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this teacher and their login?")) return;
    await api.delete(`/teachers/${id}`); load();
  };

  const toggleFront = async (t) => {
    await api.put(`/teachers/${t.id}`, { can_do_front_office: !t.can_do_front_office });
    load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Teachers</h1>
          <p className="page-sub">{list.length} teacher(s). Toggle front-office access per teacher.</p>
        </div>
        <div className="flex gap-8 flex-wrap">
          <button className="btn btn-secondary"
                  onClick={() => downloadCsv("/teachers/template.csv", "teachers_template.csv")}>
            ⬇ Template
          </button>
          <button className="btn btn-secondary"
                  onClick={() => downloadCsv("/teachers/export.csv", "teachers.csv")}>
            ⬇ Download CSV
          </button>
          <button className="btn btn-secondary"
                  disabled={importing}
                  onClick={() => fileRef.current?.click()}>
            {importing ? "Uploading…" : "⬆ Upload CSV"}
          </button>
          <input ref={fileRef} type="file" accept=".csv,text/csv"
                 style={{ display: "none" }} onChange={onFilePicked}/>
          <button className="btn" onClick={() => setCreating(true)}>+ Add teacher</button>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th><th>Employee ID</th><th>Email</th>
              <th>Subject</th><th>Classes</th><th>Front Office</th>
              <th>Status</th><th></th>
            </tr>
          </thead>
          <tbody>
            {list.map((t) => (
              <tr key={t.id}>
                <td style={{ fontWeight: 500 }}>{t.name}</td>
                <td>{t.employee_id}</td>
                <td className="text-2">{t.email}</td>
                <td>{t.subject || "—"}</td>
                <td>{t.classes_taught || "—"}</td>
                <td>
                  <button className={"pill " + (t.can_do_front_office ? "green" : "")}
                          style={{ border: "none", cursor: "pointer", fontFamily: "inherit" }}
                          onClick={() => toggleFront(t)}>
                    {t.can_do_front_office ? "Yes ✓" : "No"}
                  </button>
                </td>
                <td><span className={"pill " + (t.status === "active" ? "green" : "amber")}>{t.status}</span></td>
                <td className="num">
                  <button className="btn btn-secondary"
                          style={{ padding: "5px 10px", fontSize: 12, marginRight: 6 }}
                          onClick={() => setEditing(t)}>Edit</button>
                  <button className="btn btn-danger"
                          style={{ padding: "5px 10px", fontSize: 12 }}
                          onClick={() => remove(t.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {list.length === 0 && (
              <tr><td colSpan={8} className="empty">No teachers yet — add the first one.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {(creating || editing) && (
        <TeacherModal teacher={editing}
                      onClose={() => { setEditing(null); setCreating(false); }}
                      onSaved={() => { setEditing(null); setCreating(false); load(); }}/>
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
        <h3>{isErr ? "Teacher import failed" : "Teacher import complete"}</h3>
        {isErr ? (
          <div className="error-banner">{result.error}</div>
        ) : (
          <>
            <div className="grid grid-cols-3" style={{ marginBottom: 14 }}>
              <div className="card stat" style={{ padding: 14 }}>
                <div className="label">Created</div>
                <div className="value green">{result.created}</div>
              </div>
              <div className="card stat" style={{ padding: 14 }}>
                <div className="label">Updated</div>
                <div className="value">{result.updated}</div>
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
                      <tr key={i}><td className="tabular">{e.row}</td>
                          <td className="text-2">{e.error}</td></tr>
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

function TeacherModal({ teacher, onClose, onSaved }) {
  const editing = !!teacher;
  const [f, setF] = useState(() => editing ? {
    name: teacher.name, email: teacher.email, password: "",
    employee_id: teacher.employee_id,
    subject: teacher.subject || "",
    classes_taught: teacher.classes_taught || "",
    qualification: teacher.qualification || "",
    phone: teacher.phone || "",
    can_do_front_office: teacher.can_do_front_office,
    status: teacher.status,
  } : {
    name: "", email: "", password: "",
    employee_id: "", subject: "", classes_taught: "",
    qualification: "", phone: "",
    can_do_front_office: false, status: "active",
  });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      if (editing) {
        await api.put(`/teachers/${teacher.id}`, {
          subject: f.subject, classes_taught: f.classes_taught,
          qualification: f.qualification, phone: f.phone,
          can_do_front_office: f.can_do_front_office,
          status: f.status,
        });
      } else {
        await api.post("/teachers", f);
      }
      onSaved();
    } catch (e) { setErr(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={save} style={{ width: 540 }}>
        <h3>{editing ? `Edit ${teacher.name}` : "Add teacher"}</h3>
        {err && <div className="error-banner">{err}</div>}

        {!editing && (
          <div className="form-grid">
            <div className="form-row">
              <label>Full name</label>
              <input className="input" value={f.name} onChange={set("name")} required/>
            </div>
            <div className="form-row">
              <label>Login email</label>
              <input className="input" type="email" value={f.email} onChange={set("email")} required/>
            </div>
            <div className="form-row">
              <label>Employee ID</label>
              <input className="input" value={f.employee_id} onChange={set("employee_id")} required/>
            </div>
            <div className="form-row">
              <label>Initial password</label>
              <input className="input" type="password" value={f.password} onChange={set("password")}
                     minLength={6} required/>
            </div>
          </div>
        )}

        <div className="form-grid">
          <div className="form-row">
            <label>Subject</label>
            <input className="input" value={f.subject} onChange={set("subject")}/>
          </div>
          <div className="form-row">
            <label>Classes taught (comma)</label>
            <input className="input" value={f.classes_taught} onChange={set("classes_taught")}
                   placeholder="5,6,7"/>
          </div>
          <div className="form-row">
            <label>Qualification</label>
            <input className="input" value={f.qualification} onChange={set("qualification")}/>
          </div>
          <div className="form-row">
            <label>Phone</label>
            <input className="input" value={f.phone} onChange={set("phone")}/>
          </div>
        </div>

        <div className="form-row">
          <label>
            <input type="checkbox"
                   checked={f.can_do_front_office}
                   onChange={(e) => setF({ ...f, can_do_front_office: e.target.checked })}/>
            {" "}Allow this teacher to use the Front Office (tile-driven payments + expenses)
          </label>
        </div>

        {editing && (
          <div className="form-row">
            <label>Status</label>
            <select className="select" value={f.status} onChange={set("status")}>
              <option value="active">Active</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>
        )}

        <div className="flex gap-8" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn" disabled={busy}>{busy ? "Saving…" : (editing ? "Save" : "Create")}</button>
        </div>
      </form>
    </div>
  );
}
