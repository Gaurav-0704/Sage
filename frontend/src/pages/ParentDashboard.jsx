import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { api, fmtINR } from "../api";

export default function ParentDashboard() {
  const [children, setChildren] = useState([]);
  const [pending, setPending] = useState([]);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    api.get("/parent/me/dashboard")
      .then((r) => setChildren(r.data.children))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
    api.get("/parent/me/children")
      .then((r) => setPending(r.data.filter((c) => c.link_status !== "approved")))
      .catch(() => {});
  }, []);
  useEffect(load, [load]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">My Children</h1>
          <p className="page-sub">Attendance, marks, fees and assignments for your children.</p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      {children.length === 0 && pending.length === 0 && (
        <div className="card" style={{ padding: 16 }}>
          No approved children yet. Claim a child below — an Owner will approve the link.
        </div>
      )}

      <div className="grid grid-cols-2">
        {children.map((c) => (
          <Link key={c.student_id} to={`/child/${c.student_id}`} className="card"
                style={{ textDecoration: "none", color: "inherit" }}>
            <div className="flex between" style={{ alignItems: "flex-start" }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>{c.name}</div>
                <div className="text-2" style={{ fontSize: 12 }}>
                  Class {c.student_class}{c.section ? `-${c.section}` : ""}
                </div>
              </div>
              <span className={"pill " + (c.attendance_percentage >= 75 ? "green" : "amber")}>
                {c.attendance_percentage}% present
              </span>
            </div>
            <div className="grid grid-cols-2 mt-16">
              <div>
                <div className="text-3" style={{ fontSize: 11 }}>Fees due</div>
                <div style={{ fontWeight: 600 }} className={c.fees_due > 0 ? "red" : "green"}>
                  {fmtINR(c.fees_due)}
                </div>
              </div>
              <div>
                <div className="text-3" style={{ fontSize: 11 }}>Open assignments</div>
                <div style={{ fontWeight: 600 }}>{c.upcoming_assignments}</div>
              </div>
            </div>
            <div className="text-3 mt-16" style={{ fontSize: 12 }}>View details →</div>
          </Link>
        ))}
      </div>

      {pending.length > 0 && (
        <div className="card mt-16" style={{ padding: 14 }}>
          <div className="card-title">Awaiting approval</div>
          {pending.map((c) => (
            <div key={c.student_id} className="flex between" style={{ padding: "6px 0" }}>
              <span>{c.name} ({c.admission_no})</span>
              <span className="pill amber">{c.link_status}</span>
            </div>
          ))}
        </div>
      )}

      <ClaimChild onClaimed={load} />
    </div>
  );
}

function ClaimChild({ onClaimed }) {
  const [f, setF] = useState({ admission_no: "", phone: "" });
  const [err, setErr] = useState(""); const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault(); setErr(""); setMsg(""); setBusy(true);
    try {
      const r = await api.post("/parent/claim", f);
      setMsg(r.data.message); setF({ admission_no: "", phone: "" });
      onClaimed();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Claim failed");
    } finally { setBusy(false); }
  };

  return (
    <form className="card mt-16" style={{ padding: 14 }} onSubmit={submit}>
      <div className="card-title" style={{ marginBottom: 10 }}>Claim another child</div>
      {err && <div className="error-banner">{err}</div>}
      {msg && <div className="success-banner">{msg}</div>}
      <div className="flex gap-12 items-center flex-wrap">
        <input className="input" placeholder="Child's admission no"
               value={f.admission_no} onChange={set("admission_no")} required />
        <input className="input" placeholder="Registered phone"
               value={f.phone} onChange={set("phone")} required />
        <button className="btn" disabled={busy}>{busy ? "Submitting…" : "Claim"}</button>
      </div>
    </form>
  );
}
