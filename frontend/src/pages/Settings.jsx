import React, { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { getPref, setPref, PREF_KEYS, apply as applyPrefs } from "../preferences";

export default function Settings() {
  const { user } = useAuth();
  useEffect(() => { applyPrefs(); }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-sub">Manage your profile, sign-in, and how the app looks for you.</p>
        </div>
      </div>

      <ProfileCard user={user}/>
      <PasswordCard/>
      <DisplayCard/>
      <NotificationsCard user={user}/>
      <AccountCard user={user}/>
    </div>
  );
}

/* ---------- Profile ---------- */
function ProfileCard({ user }) {
  const [name, setName]   = useState(user?.name  || "");
  const [email, setEmail] = useState(user?.email || "");
  const [busy, setBusy]   = useState(false);
  const [msg, setMsg]     = useState(""); const [err, setErr] = useState("");

  const save = async (e) => {
    e.preventDefault(); setMsg(""); setErr(""); setBusy(true);
    try {
      const r = await api.put("/auth/me", { name, email });
      localStorage.setItem("nhs_user", JSON.stringify({
        ...JSON.parse(localStorage.getItem("nhs_user") || "{}"),
        ...r.data,
      }));
      setMsg("Profile updated. Sign out and back in for the change to take full effect.");
    } catch (e) { setErr(e?.response?.data?.detail || "Couldn't save"); }
    finally { setBusy(false); }
  };

  return (
    <form className="settings-section" onSubmit={save}>
      <h3>Profile</h3>
      <div className="subtitle">Your display name and the email you use to sign in.</div>
      {err && <div className="error-banner">{err}</div>}
      {msg && <div className="success-banner">{msg}</div>}
      <div className="form-grid">
        <div className="form-row">
          <label>Display name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)}/>
        </div>
        <div className="form-row">
          <label>Email (used for sign in)</label>
          <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)}/>
        </div>
      </div>
      <button className="btn" disabled={busy}>{busy ? "Saving…" : "Save profile"}</button>
    </form>
  );
}

/* ---------- Password ---------- */
function PasswordCard() {
  const [old_password, setOld] = useState("");
  const [new_password, setN1]  = useState("");
  const [confirm, setN2]       = useState("");
  const [msg, setMsg]          = useState(""); const [err, setErr] = useState("");
  const [busy, setBusy]        = useState(false);

  const save = async (e) => {
    e.preventDefault(); setMsg(""); setErr("");
    if (new_password.length < 6)         return setErr("New password must be at least 6 characters.");
    if (new_password !== confirm)        return setErr("New password and confirmation don't match.");
    setBusy(true);
    try {
      await api.put("/auth/me/password", { old_password, new_password });
      setMsg("Password changed.");
      setOld(""); setN1(""); setN2("");
    } catch (e) { setErr(e?.response?.data?.detail || "Couldn't change password"); }
    finally { setBusy(false); }
  };

  return (
    <form className="settings-section" onSubmit={save}>
      <h3>Sign in &amp; security</h3>
      <div className="subtitle">Change your password. Use a passphrase you'll remember.</div>
      {err && <div className="error-banner">{err}</div>}
      {msg && <div className="success-banner">{msg}</div>}
      <div className="form-row">
        <label>Current password</label>
        <input className="input" type="password" value={old_password} onChange={(e) => setOld(e.target.value)} required/>
      </div>
      <div className="form-grid">
        <div className="form-row">
          <label>New password (min 6 chars)</label>
          <input className="input" type="password" value={new_password} onChange={(e) => setN1(e.target.value)} required/>
        </div>
        <div className="form-row">
          <label>Confirm new password</label>
          <input className="input" type="password" value={confirm} onChange={(e) => setN2(e.target.value)} required/>
        </div>
      </div>
      <button className="btn" disabled={busy}>{busy ? "Saving…" : "Change password"}</button>
    </form>
  );
}

/* ---------- Display ---------- */
function DisplayCard() {
  const [compact,  setCompact]  = useState(() => getPref(PREF_KEYS.compact,  false));
  const [fontSize, setFontSize] = useState(() => getPref(PREF_KEYS.fontSize, "normal"));

  const save = (key, value) => { setPref(key, value); };

  return (
    <div className="settings-section">
      <h3>Display</h3>
      <div className="subtitle">How things look on your screen. These preferences live only on this device.</div>

      <div className="toggle-row">
        <div>
          <div className="label">Compact mode</div>
          <div className="desc">Tighter spacing — fits more on screen at the cost of breathing room.</div>
        </div>
        <button className={"toggle" + (compact ? " on" : "")}
                onClick={() => { setCompact(!compact); save(PREF_KEYS.compact, !compact); }}/>
      </div>

      <div className="toggle-row">
        <div>
          <div className="label">Font size</div>
          <div className="desc">Pick a size that's comfortable to read.</div>
        </div>
        <select className="select" style={{ width: 140, minHeight: "auto", padding: "8px 10px" }}
                value={fontSize}
                onChange={(e) => { setFontSize(e.target.value); save(PREF_KEYS.fontSize, e.target.value); }}>
          <option value="small">Small</option>
          <option value="normal">Normal</option>
          <option value="large">Large</option>
        </select>
      </div>
    </div>
  );
}

/* ---------- Notifications ---------- */
function NotificationsCard({ user }) {
  const [mail, setMail] = useState(() => getPref(PREF_KEYS.notifyMail, true));
  const save = (key, value) => { setPref(key, value); };

  return (
    <div className="settings-section">
      <h3>Notifications</h3>
      <div className="subtitle">
        How we reach you. Email is sent from {user?.role === "owner" ? "your school's address" : "the school office"}.
      </div>

      <div className="toggle-row">
        <div>
          <div className="label">Email notifications</div>
          <div className="desc">Account changes, password resets, scanner reports (Owner only).</div>
        </div>
        <button className={"toggle" + (mail ? " on" : "")}
                onClick={() => { setMail(!mail); save(PREF_KEYS.notifyMail, !mail); }}/>
      </div>
    </div>
  );
}

/* ---------- Account info ---------- */
function AccountCard({ user }) {
  return (
    <div className="settings-section">
      <h3>Account</h3>
      <div className="subtitle">Read-only info. Contact the Owner if any of this needs to change.</div>

      <div className="form-grid">
        <Field label="Role"   value={user?.role}/>
        <Field label="Status" value={user?.status}/>
        <Field label="Email"  value={user?.email}/>
        <Field label="Front-office access"
               value={user?.role === "teacher"
                  ? (user.can_do_front_office ? "Yes" : "No")
                  : "—"}/>
      </div>
    </div>
  );
}

function Field({ label, value }) {
  return (
    <div className="form-row">
      <label>{label}</label>
      <code style={{ background: "var(--surface-2)", padding: "9px 12px",
                      borderRadius: 8, fontSize: 13, color: "var(--text)" }}>
        {value || "—"}
      </code>
    </div>
  );
}
