import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";

const ROLES = [
  { v: "student", label: "Student",  hint: "I'm a student here" },
  { v: "teacher", label: "Teacher",  hint: "I teach at the school" },
  { v: "staff",   label: "Staff",    hint: "I work at the front office" },
];

export default function Signup() {
  const navigate = useNavigate();
  const [role, setRole] = useState("student");
  const [f, setF] = useState({
    name: "", email: "", password: "",
    admission_no: "", employee_id: "", subject: "",
    classes_taught: "", qualification: "", phone: "",
  });
  const [err, setErr] = useState(""); const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault(); setErr(""); setMsg(""); setBusy(true);
    const body = { name: f.name, email: f.email, password: f.password, role };
    if (role === "student") body.admission_no = f.admission_no;
    if (role === "teacher") {
      body.employee_id = f.employee_id;
      body.subject = f.subject;
      body.classes_taught = f.classes_taught;
      body.qualification = f.qualification;
      body.phone = f.phone;
    }
    try {
      const r = await api.post("/auth/signup", body);
      setMsg(r.data.message);
      if (r.data.status === "active") {
        setTimeout(() => navigate("/login"), 1500);
      }
    } catch (e) {
      setErr(e?.response?.data?.detail || "Signup failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="auth-shell">
      <form className="auth-card" onSubmit={submit} style={{ width: 480 }}>
        <div className="auth-brand">
          <div className="brand-mark">S</div>
          <h1>Create your account</h1>
          <p>Join Sage</p>
        </div>

        {err && <div className="error-banner">{err}</div>}
        {msg && <div className="success-banner">{msg}</div>}

        <div className="form-row">
          <label>I am a…</label>
          <div className="flex gap-8" style={{ flexWrap: "wrap" }}>
            {ROLES.map((r) => (
              <button type="button" key={r.v}
                      className={"icon-chip" + (role === r.v ? " on" : "")}
                      style={{ width: "auto", padding: "10px 14px" }}
                      onClick={() => setRole(r.v)}>
                {r.label}
              </button>
            ))}
          </div>
          <div className="text-3" style={{ fontSize: 11, marginTop: 4 }}>
            {ROLES.find((r) => r.v === role)?.hint}
            {role !== "student" &&
              <> · Account will be reviewed by an Owner before activation.</>}
          </div>
        </div>

        <div className="form-grid">
          <div className="form-row">
            <label>Full name</label>
            <input className="input" value={f.name} onChange={set("name")} required/>
          </div>
          <div className="form-row">
            <label>Email</label>
            <input className="input" type="email" value={f.email} onChange={set("email")} required/>
          </div>
        </div>

        <div className="form-row">
          <label>Password (min 6 chars)</label>
          <input className="input" type="password" value={f.password}
                 onChange={set("password")} minLength={6} required/>
        </div>

        {role === "student" && (
          <div className="form-row">
            <label>Admission number</label>
            <input className="input" value={f.admission_no} onChange={set("admission_no")}
                   placeholder="e.g. SGE0001" required/>
            <div className="text-3" style={{ fontSize: 11 }}>
              Must match your student record. Ask the office if you don't know it.
            </div>
          </div>
        )}

        {role === "teacher" && (
          <>
            <div className="form-grid">
              <div className="form-row">
                <label>Employee ID</label>
                <input className="input" value={f.employee_id} onChange={set("employee_id")} required/>
              </div>
              <div className="form-row">
                <label>Phone</label>
                <input className="input" value={f.phone} onChange={set("phone")}/>
              </div>
              <div className="form-row">
                <label>Primary subject</label>
                <input className="input" value={f.subject} onChange={set("subject")}
                       placeholder="e.g. Math"/>
              </div>
              <div className="form-row">
                <label>Classes taught</label>
                <input className="input" value={f.classes_taught} onChange={set("classes_taught")}
                       placeholder="e.g. 5,6,7"/>
              </div>
            </div>
            <div className="form-row">
              <label>Qualification</label>
              <input className="input" value={f.qualification} onChange={set("qualification")}
                     placeholder="e.g. M.Sc, B.Ed"/>
            </div>
          </>
        )}

        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>

        <div className="auth-link" style={{ justifyContent: "center" }}>
          <Link to="/login">← Back to sign in</Link>
        </div>
      </form>
    </div>
  );
}
