import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api, fmtINR } from "../api";
import { useAuth } from "../auth";
import CredentialsCard from "../components/CredentialsCard";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";

const SEVERITY_COLOR = {
  critical: "#dc2626",
  warning:  "#f59e0b",
  info:     "#2f6bff",
};
const SEVERITY_BG = {
  critical: "#fef2f2",
  warning:  "#fffbeb",
  info:     "#eff6ff",
};

export default function Dashboard() {
  const { user, isOwner } = useAuth();
  const navigate = useNavigate();
  const [d, setD]           = useState(null);
  const [daily, setDaily]   = useState([]);
  const [insights, setInsights] = useState([]);
  const [atRisk, setAtRisk] = useState([]);
  const [genBusy, setGenBusy] = useState(false);
  const [err, setErr]       = useState("");

  const load = useCallback(() => {
    const base = [
      api.get("/reports/dashboard"),
      api.get("/reports/daily?days=30"),
    ];
    if (isOwner) {
      base.push(api.get("/insights").catch(() => ({ data: [] })));
      base.push(api.get("/reports/at-risk?min_due=2000&days_without_payment=30&limit=5").catch(() => ({ data: [] })));
    }
    Promise.all(base)
      .then(([dash, dailyR, insR, riskR]) => {
        setD(dash.data);
        setDaily(dailyR.data);
        if (insR)  setInsights(insR.data);
        if (riskR) setAtRisk(riskR.data);
      })
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, [isOwner]);

  useEffect(() => { load(); }, [load]);

  const dismiss = async (id) => {
    await api.patch(`/insights/${id}/dismiss`).catch(() => {});
    setInsights((prev) => prev.filter((i) => i.id !== id));
  };

  const generateInsights = async () => {
    setGenBusy(true);
    try {
      const r = await api.post("/insights/generate");
      setInsights(r.data);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to generate insights");
    } finally {
      setGenBusy(false);
    }
  };

  const riskColor = (level) => ({
    critical: "#dc2626", high: "#f97316",
    medium: "#f59e0b", low: "#22c55e",
  })[level] || "#94a3b8";

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Welcome back, {user?.name?.split(" ")[0]}</h1>
          <p className="page-sub">
            {isOwner
              ? "Sage — AI-powered school ERP overview."
              : "Staff view — manage students, fees, and expenses."}
          </p>
        </div>
        <span className={"pill " + (isOwner ? "indigo" : "green")}>
          {isOwner ? "Owner" : "Staff"}
        </span>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <CredentialsCard />

      {d && (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-4 mb-16">
            <div className="card stat">
              <div className="label">Total students</div>
              <div className="value">{d.total_students}</div>
              <div className="delta">{d.active_students} active</div>
            </div>
            <div className="card stat">
              <div className="label">Total fee value</div>
              <div className="value">{fmtINR(d.total_fee_value)}</div>
              <div className="delta">incl. last-year dues</div>
            </div>
            <div className="card stat">
              <div className="label">Collected</div>
              <div className="value green">{fmtINR(d.total_collected)}</div>
              <div className="delta">{fmtINR(d.collected_today)} today</div>
            </div>
            <div className="card stat">
              <div className="label">Outstanding</div>
              <div className="value red">{fmtINR(d.total_due)}</div>
              <div className="delta">across all students</div>
            </div>
          </div>

          <div className="grid grid-cols-3 mb-16">
            <div className="card stat">
              <div className="label">Cash on hand</div>
              <div className="value">{fmtINR(d.cash_balance)}</div>
            </div>
            <div className="card stat">
              <div className="label">Bank balance</div>
              <div className="value">{fmtINR(d.bank_balance)}</div>
            </div>
            <div className="card stat">
              <div className="label">Net (collected − expenses)</div>
              <div className={"value " + (d.net >= 0 ? "green" : "red")}>
                {fmtINR(d.net)}
              </div>
              <div className="delta">expense {fmtINR(d.total_expense)}</div>
            </div>
          </div>

          {/* 30-day chart */}
          <div className="card mb-16">
            <div className="card-title">
              Last 30 days · collections vs expenses
              <span className="text-3" style={{ fontWeight: 500 }}>
                month total: {fmtINR(d.collected_this_month)} collected
              </span>
            </div>
            <div style={{ height: 240 }}>
              <ResponsiveContainer>
                <AreaChart data={daily}>
                  <defs>
                    <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2f6bff" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#2f6bff" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="eg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#dc2626" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#dc2626" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e6e8ee" />
                  <XAxis dataKey="date" tickFormatter={(d) => d?.slice(5)} fontSize={11} stroke="#94a3b8" />
                  <YAxis fontSize={11} stroke="#94a3b8" tickFormatter={(v) => "₹" + v.toLocaleString("en-IN")} />
                  <Tooltip formatter={(v) => fmtINR(v)} />
                  <Area dataKey="collected" stroke="#2f6bff" fill="url(#cg)" strokeWidth={2} />
                  <Area dataKey="expense"   stroke="#dc2626" fill="url(#eg)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* AI Insights (owner only) */}
          {isOwner && (
            <div className="card mb-16">
              <div className="card-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span>AI Insights</span>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  {insights.length > 0 && (
                    <span className="text-3" style={{ fontSize: 12 }}>
                      {insights.length} active · generated {new Date(insights[0]?.generated_at).toLocaleDateString()}
                    </span>
                  )}
                  <button className="btn btn-secondary" style={{ padding: "4px 12px", fontSize: 12 }}
                          onClick={generateInsights} disabled={genBusy}>
                    {genBusy ? "Analysing…" : "↺ Refresh"}
                  </button>
                </div>
              </div>

              {insights.length === 0 ? (
                <div style={{ padding: "24px 0", textAlign: "center", color: "var(--text-3)" }}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>🤖</div>
                  <div style={{ fontSize: 13 }}>No insights yet.</div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>
                    Click Refresh to have Claude analyse your school data.
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {insights.map((ins) => (
                    <div key={ins.id} style={{
                      borderLeft: `3px solid ${SEVERITY_COLOR[ins.severity]}`,
                      background: SEVERITY_BG[ins.severity],
                      borderRadius: "0 8px 8px 0",
                      padding: "10px 14px",
                      display: "flex", gap: 12, alignItems: "flex-start",
                    }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 4 }}>
                          <span style={{
                            fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                            letterSpacing: ".06em", color: SEVERITY_COLOR[ins.severity],
                          }}>{ins.severity}</span>
                          <span style={{ fontSize: 11, color: "var(--text-3)", background: "rgba(0,0,0,.06)",
                                          borderRadius: 4, padding: "1px 6px" }}>{ins.category}</span>
                          <span style={{ fontSize: 13, fontWeight: 600 }}>{ins.title}</span>
                        </div>
                        <div style={{ fontSize: 13, color: "var(--text-2)", marginBottom: ins.action_hint ? 6 : 0 }}>
                          {ins.body}
                        </div>
                        {ins.action_hint && (
                          <button
                            className="btn btn-secondary"
                            style={{ fontSize: 11, padding: "3px 10px", marginTop: 2 }}
                            onClick={() => navigate("/assistant", { state: { prefill: ins.action_hint } })}
                          >
                            → Ask assistant: "{ins.action_hint.slice(0, 60)}{ins.action_hint.length > 60 ? "…" : ""}"
                          </button>
                        )}
                      </div>
                      <button
                        onClick={() => dismiss(ins.id)}
                        style={{ background: "none", border: "none", cursor: "pointer",
                                  color: "var(--text-3)", fontSize: 16, padding: 0, flexShrink: 0 }}
                        title="Dismiss"
                      >×</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* At-Risk students (owner only) */}
          {isOwner && atRisk.length > 0 && (
            <div className="card">
              <div className="card-title" style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Fee Risk Watch</span>
                <button className="btn btn-secondary" style={{ fontSize: 12, padding: "4px 12px" }}
                        onClick={() => navigate("/students")}>
                  View all students →
                </button>
              </div>
              <p style={{ fontSize: 12, color: "var(--text-3)", margin: "0 0 12px" }}>
                Active students with outstanding dues and no payment in 30+ days.
              </p>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    {["Student", "Class", "Outstanding", "Last payment", "Risk"].map((h) => (
                      <th key={h} style={{ textAlign: "left", padding: "6px 8px",
                                            color: "var(--text-3)", fontWeight: 600, fontSize: 11 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {atRisk.map((r) => (
                    <tr key={r.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "8px 8px" }}>
                        <div style={{ fontWeight: 500 }}>{r.name}</div>
                        <div style={{ fontSize: 11, color: "var(--text-3)" }}>{r.admission_no}</div>
                      </td>
                      <td style={{ padding: "8px 8px" }}>{r.student_class}{r.section ? `-${r.section}` : ""}</td>
                      <td style={{ padding: "8px 8px", fontWeight: 600, color: "#dc2626" }}>{fmtINR(r.due)}</td>
                      <td style={{ padding: "8px 8px", color: "var(--text-3)", fontSize: 12 }}>
                        {r.days_since_payment != null ? `${r.days_since_payment}d ago` : "Never"}
                      </td>
                      <td style={{ padding: "8px 8px" }}>
                        <span style={{
                          background: riskColor(r.risk_level) + "22",
                          color: riskColor(r.risk_level),
                          border: `1px solid ${riskColor(r.risk_level)}44`,
                          borderRadius: 6, padding: "2px 8px",
                          fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                        }}>{r.risk_level}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
