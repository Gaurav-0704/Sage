import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";

export default function ForgotPassword() {
  const [stage, setStage] = useState("email");   // "email" | "reset"
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [pwd, setPwd] = useState("");
  const [err, setErr] = useState(""); const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const requestCode = async (e) => {
    e.preventDefault(); setErr(""); setMsg(""); setBusy(true);
    try {
      const r = await api.post("/auth/forgot", { email });
      setMsg(r.data.message);
      setStage("reset");
    } catch (e) { setErr(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  const reset = async (e) => {
    e.preventDefault(); setErr(""); setMsg(""); setBusy(true);
    try {
      await api.post("/auth/reset", { email, code, new_password: pwd });
      setMsg("Password updated. Redirecting to sign-in…");
      setTimeout(() => navigate("/login"), 1500);
    } catch (e) { setErr(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="brand-mark">N</div>
          <h1>{stage === "email" ? "Forgot password" : "Verify code"}</h1>
          <p>
            {stage === "email"
              ? "Enter your email — we'll send a 6-digit code."
              : `Code was sent to ${email}.`}
          </p>
        </div>

        {err && <div className="error-banner">{err}</div>}
        {msg && <div className="success-banner">{msg}</div>}

        {stage === "email" ? (
          <form onSubmit={requestCode}>
            <div className="form-row">
              <label>Email</label>
              <input className="input" type="email" value={email}
                     onChange={(e) => setEmail(e.target.value)} required/>
            </div>
            <button className="btn" disabled={busy}>{busy ? "Sending…" : "Send code"}</button>
          </form>
        ) : (
          <form onSubmit={reset}>
            <div className="form-row">
              <label>6-digit code</label>
              <input className="input tabular" inputMode="numeric"
                     value={code} maxLength={6}
                     onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                     required/>
            </div>
            <div className="form-row">
              <label>New password (min 6 chars)</label>
              <input className="input" type="password" value={pwd} minLength={6}
                     onChange={(e) => setPwd(e.target.value)} required/>
            </div>
            <button className="btn" disabled={busy}>{busy ? "Resetting…" : "Reset password"}</button>
            <div className="auth-link">
              <button type="button" className="btn btn-secondary"
                      style={{ padding: "6px 10px", fontSize: 11 }}
                      onClick={() => setStage("email")}>
                ← Use a different email
              </button>
            </div>
          </form>
        )}

        <div className="auth-hint" style={{ marginTop: 18 }}>
          <strong>Dev mode</strong>: if SMTP isn't configured, the code is printed
          to the backend terminal and saved in the Owner → Notifications page.
        </div>

        <div className="auth-link" style={{ justifyContent: "center", marginTop: 14 }}>
          <Link to="/login">← Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}
