import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api";

export default function OwnerAudit() {
  const [logs, setLogs]       = useState([]);
  const [summary, setSummary] = useState(null);
  const [actors, setActors]   = useState([]);
  const [view, setView]       = useState("table");   // table | timeline
  const [filters, setFilters] = useState({
    role: "", method: "", days: 7, search: "", user_name: "",
  });
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    const params = { days: filters.days };
    if (filters.role)      params.role      = filters.role;
    if (filters.method)    params.method    = filters.method;
    if (filters.search)    params.search    = filters.search;
    if (filters.user_name) params.user_name = filters.user_name;
    Promise.all([
      api.get("/audit/logs", { params }),
      api.get(`/audit/summary?days=${filters.days}`),
      api.get(`/audit/actors?days=${filters.days}`),
    ]).then(([a, b, c]) => { setLogs(a.data); setSummary(b.data); setActors(c.data); })
      .catch((e) => setErr(e?.response?.data?.detail || "Failed"));
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const set = (k, v) => setFilters((f) => ({ ...f, [k]: v }));

  // Group logs by date for timeline view
  const byDate = logs.reduce((acc, l) => {
    const d = new Date(l.created_at).toLocaleDateString("en-IN", {
      day: "2-digit", month: "short", year: "numeric",
    });
    (acc[d] = acc[d] || []).push(l);
    return acc;
  }, {});

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Audit Log</h1>
          <p className="page-sub">Every state-changing action by every user — searchable and filterable.</p>
        </div>
        <div className="flex gap-8">
          <button className={"btn " + (view === "table"    ? "" : "btn-secondary")}
                  onClick={() => setView("table")}>Table</button>
          <button className={"btn " + (view === "timeline" ? "" : "btn-secondary")}
                  onClick={() => setView("timeline")}>Timeline</button>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      {/* Filters */}
      <div className="card mb-16" style={{ padding: 14 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <input className="input" placeholder="Search actions, paths, users…"
                 value={filters.search} style={{ flex: 1, minWidth: 180 }}
                 onChange={(e) => set("search", e.target.value)} />
          <select className="select" value={filters.role} style={{ width: 130 }}
                  onChange={(e) => set("role", e.target.value)}>
            <option value="">All roles</option>
            <option value="owner">Owner</option>
            <option value="staff">Staff</option>
            <option value="teacher">Teacher</option>
            <option value="student">Student</option>
          </select>
          <select className="select" value={filters.user_name} style={{ width: 160 }}
                  onChange={(e) => set("user_name", e.target.value)}>
            <option value="">All actors</option>
            {actors.map((a) => (
              <option key={a.id} value={a.name}>{a.name} ({a.role})</option>
            ))}
          </select>
          <select className="select" value={filters.method} style={{ width: 140 }}
                  onChange={(e) => set("method", e.target.value)}>
            <option value="">All methods</option>
            <option value="POST">POST (create)</option>
            <option value="PUT">PUT (update)</option>
            <option value="DELETE">DELETE</option>
            <option value="PATCH">PATCH</option>
          </select>
          <select className="select" value={filters.days} style={{ width: 130 }}
                  onChange={(e) => set("days", Number(e.target.value))}>
            <option value="1">Last 24h</option>
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
          <span className="text-3" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
            {logs.length} result{logs.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Activity summary */}
      {summary && Object.keys(summary).length > 0 && (
        <div className="card mb-16">
          <div className="card-title">Activity by role · last {filters.days} days</div>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            {Object.entries(summary).map(([role, methods]) => (
              <div key={role} style={{ background: "var(--surface-2)", borderRadius: 8,
                                        padding: "10px 16px", minWidth: 140 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-2)",
                               textTransform: "uppercase", marginBottom: 6 }}>{role}</div>
                {Object.entries(methods).map(([m, c]) => (
                  <div key={m} style={{ display: "flex", justifyContent: "space-between",
                                         gap: 16, fontSize: 13 }}>
                    <span className={"pill " + methodPill(m)} style={{ fontSize: 10 }}>{m}</span>
                    <span style={{ fontWeight: 600 }}>{c}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Table view */}
      {view === "table" && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Time</th><th>User</th><th>Role</th><th>Action</th>
                <th>Method</th><th>Path</th><th className="num">Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td className="text-2 tabular" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                    {new Date(l.created_at).toLocaleString("en-IN", {
                      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
                    })}
                  </td>
                  <td style={{ fontWeight: 500 }}>{l.user_name || "—"}</td>
                  <td><span className="pill">{l.user_role || "?"}</span></td>
                  <td style={{ fontWeight: 500 }}>{l.summary}</td>
                  <td><span className={"pill " + methodPill(l.method)}>{l.method}</span></td>
                  <td className="text-2 tabular" style={{ fontSize: 11 }}>{l.path}</td>
                  <td className="num">
                    <span className={"pill " + (l.status_code < 400 ? "green" : "red")}>
                      {l.status_code}
                    </span>
                  </td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={7} className="empty">No actions in this window.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Timeline view */}
      {view === "timeline" && (
        <div style={{ paddingLeft: 8 }}>
          {Object.keys(byDate).length === 0 && (
            <div className="card" style={{ textAlign: "center", padding: 32, color: "var(--text-3)" }}>
              No activity in this window.
            </div>
          )}
          {Object.entries(byDate).map(([day, dayLogs]) => (
            <div key={day} style={{ marginBottom: 28 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-3)",
                             textTransform: "uppercase", letterSpacing: ".06em",
                             marginBottom: 10, paddingLeft: 28 }}>{day}</div>
              {dayLogs.map((l, i) => (
                <div key={l.id} style={{ display: "flex", gap: 14, marginBottom: 10 }}>
                  {/* Timeline spine */}
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 20 }}>
                    <div style={{
                      width: 10, height: 10, borderRadius: "50%", flexShrink: 0,
                      background: methodColor(l.method), marginTop: 4,
                    }} />
                    {i < dayLogs.length - 1 && (
                      <div style={{ width: 2, flex: 1, background: "var(--border)", marginTop: 2 }} />
                    )}
                  </div>
                  <div className="card" style={{ flex: 1, padding: "10px 14px", marginBottom: 0 }}>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{l.summary}</span>
                      <span className={"pill " + methodPill(l.method)} style={{ fontSize: 10 }}>{l.method}</span>
                      <span className={"pill " + (l.status_code < 400 ? "green" : "red")}
                            style={{ fontSize: 10 }}>{l.status_code}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 4 }}>
                      {l.user_name ? (
                        <><span style={{ fontWeight: 500 }}>{l.user_name}</span> ({l.user_role})</>
                      ) : "Anonymous"}{" · "}
                      {new Date(l.created_at).toLocaleTimeString("en-IN", {
                        hour: "2-digit", minute: "2-digit",
                      })}{" · "}
                      <span style={{ fontFamily: "ui-monospace, monospace" }}>{l.path}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function methodPill(m) {
  return ({ POST: "green", PUT: "indigo", DELETE: "red", PATCH: "amber" })[m] || "";
}
function methodColor(m) {
  return ({ POST: "#22c55e", PUT: "#6366f1", DELETE: "#dc2626", PATCH: "#f59e0b" })[m] || "#94a3b8";
}
