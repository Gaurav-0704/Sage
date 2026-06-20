import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function Notifications() {
  const [list, setList] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/auth/notifications?limit=100")
      .then((r) => setList(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed"));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Notifications</h1>
          <p className="page-sub">
            All system-sent emails. Useful in dev mode when SMTP isn't configured —
            you can read the password-reset codes here too.
          </p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      {list.length === 0 ? (
        <div className="empty">No notifications yet.</div>
      ) : list.map((n) => (
        <div key={n.id} className="card mb-16">
          <div className="flex between items-center mb-16">
            <div>
              <div style={{ fontWeight: 700 }}>{n.subject}</div>
              <div className="text-3" style={{ fontSize: 12 }}>
                to: {n.to_email} · {new Date(n.created_at).toLocaleString()}
              </div>
            </div>
            <span className={"pill " + (n.delivered ? "green" : "amber")}>
              {n.delivered ? "delivered" : "logged only"}
            </span>
          </div>
          <pre style={{
            margin: 0, whiteSpace: "pre-wrap", fontFamily: "inherit",
            color: "var(--text-2)", fontSize: 13, lineHeight: 1.5,
          }}>{n.body}</pre>
        </div>
      ))}
    </div>
  );
}
