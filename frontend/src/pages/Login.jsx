import React, { useState } from "react";
import { useNavigate, Navigate, Link } from "react-router-dom";
import { useAuth } from "../auth";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (e) {
      setErr(e?.response?.data?.detail || "Login failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="auth-shell">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-brand">
          <div className="brand-mark">S</div>
          <h1>Sage</h1>
          <p>Sign in to your account</p>
        </div>

        {err && <div className="error-banner">{err}</div>}

        <div className="form-row">
          <label>Email</label>
          <input className="input" type="email" value={email}
                 onChange={(e) => setEmail(e.target.value)}
                 placeholder="you@sage.school"
                 autoComplete="email" autoFocus required/>
        </div>
        <div className="form-row">
          <label>Password</label>
          <input className="input" type="password" value={password}
                 onChange={(e) => setPassword(e.target.value)}
                 placeholder="Your password"
                 autoComplete="current-password" required/>
        </div>
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>

        <div className="auth-link">
          <Link to="/forgot">Forgot password?</Link>
          <Link to="/signup">Create an account</Link>
        </div>

        <div className="auth-hint">
          <strong>Demo accounts</strong><br/>
          Owner: owner@sage.school / owner123<br/>
          Staff: staff@sage.school / staff123<br/>
          Teachers / Students: see <code>tools/seed_demo.py</code> output
        </div>

        <div style={{ textAlign: "center", marginTop: 16, fontSize: 11, color: "var(--text-3)" }}>
          © 2026 Gaurav Singh Thakur
        </div>
      </form>
    </div>
  );
}
