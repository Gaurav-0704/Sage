import React, { useEffect, useState } from "react";
import { api, fmtINR } from "../api";
import { useAuth } from "../auth";
import CredentialsCard from "../components/CredentialsCard";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";

export default function Dashboard() {
  const { user, isOwner } = useAuth();
  const [d, setD] = useState(null);
  const [daily, setDaily] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([
      api.get("/reports/dashboard"),
      api.get("/reports/daily?days=30"),
    ])
      .then(([a, b]) => { setD(a.data); setDaily(b.data); })
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Welcome back, {user?.name?.split(" ")[0]}</h1>
          <p className="page-sub">
            {isOwner
              ? "Read-only owner view — full reports and balances."
              : "Staff view — manage students, fees, and expenses."}
          </p>
        </div>
        <span className={"pill " + (isOwner ? "indigo" : "green")}>
          {isOwner ? "Owner" : "Staff"}
        </span>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <CredentialsCard/>

      {d && (
        <>
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
              <div className="label">Remaining to collect</div>
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

          <div className="card">
            <div className="card-title">
              Last 30 days · collections vs expenses
              <span className="text-3" style={{ fontWeight: 500 }}>
                month total: {fmtINR(d.collected_this_month)} collected
              </span>
            </div>
            <div style={{ height: 260 }}>
              <ResponsiveContainer>
                <AreaChart data={daily}>
                  <defs>
                    <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2f6bff" stopOpacity={0.35}/>
                      <stop offset="100%" stopColor="#2f6bff" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="eg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#dc2626" stopOpacity={0.25}/>
                      <stop offset="100%" stopColor="#dc2626" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e6e8ee"/>
                  <XAxis dataKey="date" tickFormatter={(d)=>d?.slice(5)} fontSize={11} stroke="#94a3b8"/>
                  <YAxis fontSize={11} stroke="#94a3b8" tickFormatter={(v)=>"₹"+v.toLocaleString("en-IN")}/>
                  <Tooltip formatter={(v)=>fmtINR(v)}/>
                  <Area dataKey="collected" stroke="#2f6bff" fill="url(#cg)" strokeWidth={2}/>
                  <Area dataKey="expense"   stroke="#dc2626" fill="url(#eg)" strokeWidth={2}/>
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
