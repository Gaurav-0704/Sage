import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api";

export default function OwnerApprovals() {
  const [list, setList] = useState([]);
  const [links, setLinks] = useState([]);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    api.get("/auth/pending")
      .then((r) => setList(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed"));
    api.get("/parent/links", { params: { status: "pending" } })
      .then((r) => setLinks(r.data))
      .catch(() => {});
  }, []);
  useEffect(load, [load]);

  const approveLink = async (l) => { await api.post(`/parent/links/${l.id}/approve`); load(); };
  const rejectLink = async (l) => { await api.post(`/parent/links/${l.id}/reject`); load(); };

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
        <div className="empty">No accounts to approve. ✨</div>
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
              {u.role === "parent" && (
                <div className="text-3" style={{ fontSize: 11, marginTop: 8 }}>
                  Approving also approves this parent's pending child link(s).
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {links.length > 0 && (
        <>
          <h2 className="page-title" style={{ fontSize: 18, marginTop: 28 }}>
            Parent child-claims ({links.length})
          </h2>
          <p className="page-sub">Additional children claimed by already-active parents.</p>
          <div className="grid grid-cols-2">
            {links.map((l) => (
              <div key={l.id} className="card">
                <div className="flex between" style={{ alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 15 }}>{l.parent_name}</div>
                    <div className="text-2" style={{ fontSize: 12 }}>{l.parent_email}</div>
                  </div>
                  <span className="pill amber">claim</span>
                </div>
                <div className="text-2 mt-16" style={{ fontSize: 13 }}>
                  Child: <b>{l.student_name}</b> ({l.admission_no})
                </div>
                <div className="flex gap-8 mt-16">
                  <button className="btn" onClick={() => approveLink(l)}>✓ Approve link</button>
                  <button className="btn btn-danger" onClick={() => rejectLink(l)}>✗ Reject</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
