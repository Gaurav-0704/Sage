import React, { useEffect, useState } from "react";
import { api, fmtINR } from "../api";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";

export default function Reports() {
  const [monthly, setMonthly] = useState([]);
  const [yearly,  setYearly]  = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([
      api.get("/reports/monthly?months=12"),
      api.get("/reports/yearly"),
    ])
      .then(([a, b]) => { setMonthly(a.data); setYearly(b.data); })
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);

  const downloadCSV = (rows, name) => {
    if (!rows.length) return;
    const cols = Object.keys(rows[0]);
    const csv = [
      cols.join(","),
      ...rows.map((r) => cols.map((c) => JSON.stringify(r[c] ?? "")).join(",")),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = name; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Reports</h1>
          <p className="page-sub">Monthly and yearly aggregates. Owner-friendly read-only view.</p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div className="card mb-16">
        <div className="card-title">
          Last 12 months
          <button className="btn btn-secondary" style={{ padding: "6px 10px", fontSize: 12 }}
                  onClick={() => downloadCSV(monthly, "monthly_report.csv")}>
            ⬇ Download CSV
          </button>
        </div>
        <div style={{ height: 280 }}>
          <ResponsiveContainer>
            <BarChart data={monthly}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e6e8ee"/>
              <XAxis dataKey="month" fontSize={11} stroke="#94a3b8"/>
              <YAxis fontSize={11} stroke="#94a3b8" tickFormatter={(v)=>"₹"+v.toLocaleString("en-IN")}/>
              <Tooltip formatter={(v)=>fmtINR(v)}/>
              <Legend wrapperStyle={{ fontSize: 12 }}/>
              <Bar dataKey="collected" fill="#2f6bff" radius={[4,4,0,0]}/>
              <Bar dataKey="expense"   fill="#dc2626" radius={[4,4,0,0]}/>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <table className="table mt-16">
          <thead>
            <tr><th>Month</th><th className="num">Collected</th><th className="num">Expense</th><th className="num">Net</th></tr>
          </thead>
          <tbody>
            {monthly.map((r) => (
              <tr key={r.month}>
                <td>{r.month}</td>
                <td className="num">{fmtINR(r.collected)}</td>
                <td className="num">{fmtINR(r.expense)}</td>
                <td className="num" style={{ fontWeight: 600, color: r.net >= 0 ? "var(--green)" : "var(--red)" }}>
                  {fmtINR(r.net)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="card-title">
          Yearly summary
          <button className="btn btn-secondary" style={{ padding: "6px 10px", fontSize: 12 }}
                  onClick={() => downloadCSV(yearly, "yearly_report.csv")}>
            ⬇ Download CSV
          </button>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Academic year</th>
              <th className="num">Total fee value</th>
              <th className="num">Collected</th>
              <th className="num">Due</th>
              <th className="num">Expense</th>
              <th className="num">Net</th>
            </tr>
          </thead>
          <tbody>
            {yearly.map((r) => (
              <tr key={r.academic_year}>
                <td>{r.academic_year}</td>
                <td className="num">{fmtINR(r.total_fee_value)}</td>
                <td className="num">{fmtINR(r.total_collected)}</td>
                <td className="num">{fmtINR(r.total_due)}</td>
                <td className="num">{fmtINR(r.total_expense)}</td>
                <td className="num" style={{ fontWeight: 600, color: r.net >= 0 ? "var(--green)" : "var(--red)" }}>
                  {fmtINR(r.net)}
                </td>
              </tr>
            ))}
            {yearly.length === 0 && (
              <tr><td colSpan={6} className="empty">
                No fee bills generated yet. Create a fee structure and apply it on the Fees page.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
