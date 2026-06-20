import React, { useState } from "react";
import { useAuth } from "../auth";

/**
 * Shows the signed-in user's email + the seeded default password
 * for the demo accounts. Other accounts get a friendly placeholder.
 *
 * The Owner gets a "Show all demo credentials" toggle that lists every
 * built-in login for quick testing.
 */
const DEFAULT_PWD = {
  owner:   "owner123",
  staff:   "staff123",
  teacher: "teacher123",
  student: "student123",
};

const ALL_DEMO = [
  { role: "owner",   email: "owner@nagarjuna.school", pwd: "owner123",   name: "School Owner" },
  { role: "staff",   email: "staff@nagarjuna.school", pwd: "staff123",   name: "Front Office" },
  { role: "teacher", email: "sunita.iyer@nagarjuna.school",   pwd: "teacher123", name: "Sunita Iyer (Math, KG-2, can do front office)" },
  { role: "teacher", email: "karthik.menon@nagarjuna.school", pwd: "teacher123", name: "Karthik Menon (Math 5-7, can do front office)" },
  { role: "teacher", email: "meera.bose@nagarjuna.school",    pwd: "teacher123", name: "Meera Bose (English 5-8, can do front office)" },
  { role: "teacher", email: "geetha.joshi@nagarjuna.school",  pwd: "teacher123", name: "Geetha Joshi (Hindi 6-10, can do front office)" },
  { role: "teacher", email: "anil.kapoor@nagarjuna.school",   pwd: "teacher123", name: "Anil Kapoor (Math 8-10)" },
  { role: "student", email: "nhs0001@nagarjuna.school", pwd: "student123", name: "Student #1 (any nhs0001..nhs0300 works)" },
  { role: "student", email: "nhs0150@nagarjuna.school", pwd: "student123", name: "Student #150 (try this for class 5)" },
];

export default function CredentialsCard() {
  const { user } = useAuth();
  const [show, setShow] = useState(false);
  const [showAll, setShowAll] = useState(false);
  if (!user) return null;

  const isDemo = (
    (user.role === "owner"   && user.email === "owner@nagarjuna.school") ||
    (user.role === "staff"   && user.email === "staff@nagarjuna.school") ||
    (user.role === "teacher" && user.email.endsWith("@nagarjuna.school")) ||
    (user.role === "student" && /^nhs\d{4}@nagarjuna\.school$/.test(user.email))
  );
  const defaultPwd = DEFAULT_PWD[user.role];

  return (
    <div className="card mb-16">
      <div className="card-title">
        🔑 Login credentials
        {user.role === "owner" && (
          <button className="btn btn-secondary"
                  style={{ padding: "4px 10px", fontSize: 11 }}
                  onClick={() => setShowAll((v) => !v)}>
            {showAll ? "Hide all demo accounts" : "Show all demo accounts"}
          </button>
        )}
      </div>

      <div className="grid grid-cols-2">
        <Field label="Username (email)" value={user.email} mono/>
        <Field
          label="Password"
          mono
          value={
            isDemo
              ? (show ? defaultPwd : "•".repeat((defaultPwd || "").length || 8))
              : "(your custom password)"
          }
          extra={
            isDemo && (
              <button className="btn btn-secondary"
                      style={{ padding: "3px 8px", fontSize: 11, marginLeft: 8 }}
                      onClick={() => setShow((v) => !v)}>
                {show ? "Hide" : "Show"}
              </button>
            )
          }
        />
      </div>

      <div className="text-3" style={{ fontSize: 11, marginTop: 10 }}>
        {isDemo
          ? "This is a seeded demo account. Change the password from Settings → Change password."
          : "We can't display custom passwords. If you forgot it, sign out and use Forgot password."}
      </div>

      {showAll && (
        <div className="table-wrap" style={{ marginTop: 16 }}>
          <table className="table">
            <thead>
              <tr><th>Role</th><th>Email</th><th>Password</th><th>Notes</th></tr>
            </thead>
            <tbody>
              {ALL_DEMO.map((d, i) => (
                <tr key={i}>
                  <td><span className="pill indigo">{d.role}</span></td>
                  <td className="tabular">{d.email}</td>
                  <td className="tabular">{d.pwd}</td>
                  <td className="text-2">{d.name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Field({ label, value, mono, extra }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div className="text-2" style={{ fontSize: 11, fontWeight: 600 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "center" }}>
        <code style={{
          background: "var(--surface-2)",
          padding: "6px 10px", borderRadius: 6,
          color: "var(--text)",
          fontFamily: mono ? "ui-monospace, Consolas, monospace" : "inherit",
          fontSize: 13, flex: 1,
        }}>{value}</code>
        {extra}
      </div>
    </div>
  );
}
