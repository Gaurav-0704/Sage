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
  { role: "owner",   email: "owner@sage.school", pwd: "owner123",   name: "School Owner" },
  { role: "staff",   email: "staff@sage.school", pwd: "staff123",   name: "Front Office" },
  { role: "teacher", email: "teacher1@sage.school",  pwd: "teacher123", name: "Teacher 1 (can do front office)" },
  { role: "teacher", email: "teacher2@sage.school",  pwd: "teacher123", name: "Teacher 2 (can do front office)" },
  { role: "teacher", email: "teacher3@sage.school",  pwd: "teacher123", name: "Teacher 3" },
  { role: "student", email: "sage0001@sage.school", pwd: "student123", name: "Student #1 (any sage0001..sage0500 works)" },
  { role: "student", email: "sage0150@sage.school", pwd: "student123", name: "Student #150" },
];

export default function CredentialsCard() {
  const { user } = useAuth();
  const [show, setShow] = useState(false);
  const [showAll, setShowAll] = useState(false);
  if (!user) return null;

  const isDemo = (
    (user.role === "owner"   && user.email === "owner@sage.school") ||
    (user.role === "staff"   && user.email === "staff@sage.school") ||
    (user.role === "teacher" && user.email.endsWith("@sage.school")) ||
    (user.role === "student" && /^sage\d{4}@sage\.school$/.test(user.email))
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
