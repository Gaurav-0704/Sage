import React, { useEffect, useState, useCallback } from "react";
import { api, fmtDate } from "../api";

export default function OwnerApprovals() {
  const [list, setList] = useState([]);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    api.get("/auth/pending")
      .then((r) => setList(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed"));
  }, []);
  useEffect(load, [load]);

  const approve = async (u, can_front = false) => {
    await api.post(`/auth/users/${u.id}/approve`,
                    { can_do_front_office: u.role === "teacher" ? can_front : null });
    load();
  };
  const reject = async (u) => {
    if (!window.confirm(`Reject ${u.name}?`)) return;
    await api.delete(`/auth/users/${u.id}`); load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Pending Approvals</h1>
          <p className="page-sub">{list.length} account(s) waiting for review.</p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      {list.length === 0 ? (
        <div className="empty">Nothing to approve. ✨</div>
      ) : (
        <div className="grid grid-cols-2">
          {list.map((u) => (
            <div key={u.id} className="card">
              <div className="flex between" style={{ alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15 }}>{u.name}</div>
                  <div className="text-2" style={{ fontSize: 12 }}>{u.email}</div>
                </div>
                <span className="pill amber">{u.role}</span>
              </div>
              <div className="flex gap-8 mt-16">
                {u.role === "teacher" && (
                  <button className="btn btn-secondary"
                          onClick={() => approve(u, true)}>
                    ✓ Approve + Front Office
                  </button>
                )}
                <button className="btn" onClick={() => approve(u)}>✓ Approve</button>
                <button className="btn btn-danger" onClick={() => reject(u)}>✗ Reject</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
