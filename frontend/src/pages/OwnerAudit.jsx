import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api";

export default function OwnerAudit() {
  const [logs, setLogs] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filters, setFilters] = useState({ role: "", method: "", days: 7 });
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    const params = { days: filters.days };
    if (filters.role)   params.role = filters.role;
    if (filters.method) params.method = filters.method;
    Promise.all([
      api.get("/audit/logs", { params }),
      api.get(`/audit/summary?days=${filters.days}`),
    ]).then(([a, b]) => { setLogs(a.data); setSummary(b.data); })
      .catch((e) => setErr(e?.response?.data?.detail || "Failed"));
  }, [filters]);
  useEffect(load, [load]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Audit Log</h1>
          <p className="page-sub">Every change made by every user.</p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div className="card mb-16" style={{ padding: 14 }}>
        <div className="flex gap-12 items-center">
          <span className="text-2" style={{ fontSize: 12, fontWeight: 600 }}>Filters</span>
          <select className="select" value={filters.role} style={{ width: 140 }}
                  onChange={(e) => setFilters({ ...filters, role: e.target.value })}>
            <option value="">All roles</option>
            <option value="owner">Owner</option>
            <option value="staff">Staff</option>
            <option value="teacher">Teacher</option>
            <option value="student">Student</option>
          </select>
          <select className="select" value={filters.method} style={{ width: 140 }}
                  onChange={(e) => setFilters({ ...filters, method: e.target.value })}>
            <option value="">All methods</option>
            <option value="POST">POST (create)</option>
            <option value="PUT">PUT (update)</option>
            <option value="DELETE">DELETE</option>
          </select>
          <select className="select" value={filters.days} style={{ width: 140 }}
                  onChange={(e) => setFilters({ ...filters, days: Number(e.target.value) })}>
            <option value="1">Last 24h</option>
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
        </div>
      </div>

      {summary && (
        <div className="card mb-16">
          <div className="card-title">Activity by role · last {filters.days} days</div>
          <table className="table">
            <thead>
              <tr><th>Role</th><th className="num">POST</th><th className="num">PUT</th><th className="num">DELETE</th></tr>
            </thead>
            <tbody>
              {Object.entries(summary).map(([role, methods]) => (
                <tr key={role}>
                  <td><span className="pill indigo">{role}</span></td>
                  <td className="num">{methods.POST   || 0}</td>
                  <td className="num">{methods.PUT    || 0}</td>
                  <td className="num">{methods.DELETE || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Time</th><th>User</th><th>Role</th><th>Action</th><th>Method</th><th>Path</th><th className="num">Status</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id}>
                <td className="text-2 tabular" style={{ fontSize: 12 }}>
                  {new Date(l.created_at).toLocaleString()}
                </td>
                <td>{l.user_name || "—"}</td>
                <td><span className="pill">{l.user_role || "?"}</span></td>
                <td style={{ fontWeight: 500 }}>{l.summary}</td>
                <td><span className={"pill " + methodPill(l.method)}>{l.method}</span></td>
                <td className="text-2 tabular" style={{ fontSize: 12 }}>{l.path}</td>
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
    </div>
  );
}

function methodPill(m) {
  return ({ POST: "green", PUT: "indigo", DELETE: "red", PATCH: "amber" })[m] || "";
}
