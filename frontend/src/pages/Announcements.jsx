import React, { useEffect, useState, useCallback } from "react";
import { api, fmtDate } from "../api";
import { useAuth } from "../auth";
import { CLASS_ORDER } from "../school";

const AUDIENCES = ["all", "students", "parents", "teachers", "staff"];
const CAN_POST = ["owner", "staff", "teacher"];

export default function Announcements() {
  const { user } = useAuth();
  const canPost = CAN_POST.includes(user?.role);
  const [feed, setFeed] = useState([]);
  const [mine, setMine] = useState([]);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    api.get("/announcements/feed")
      .then((r) => setFeed(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
    if (canPost) {
      api.get("/announcements").then((r) => setMine(r.data)).catch(() => {});
    }
  }, [canPost]);
  useEffect(load, [load]);

  const remove = async (id) => {
    if (!window.confirm("Delete this announcement?")) return;
    await api.delete(`/announcements/${id}`); load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Notice Board</h1>
          <p className="page-sub">Announcements for you.</p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      {canPost && <NewAnnouncement role={user.role} onPosted={load} />}

      <div className="grid grid-cols-2">
        {feed.map((a) => (
          <div key={a.id} className="card">
            <div className="flex between items-center">
              <div style={{ fontWeight: 700, fontSize: 15 }}>{a.title}</div>
              <span className="pill">{a.audience}{a.student_class ? ` · ${a.student_class}` : ""}</span>
            </div>
            <div style={{ marginTop: 8, fontSize: 13, color: "var(--text-2)", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
              {a.body}
            </div>
            <div className="text-3" style={{ fontSize: 11, marginTop: 10 }}>
              {a.created_by_name || "School"} · {fmtDate(a.created_at)}
            </div>
          </div>
        ))}
        {feed.length === 0 && <div className="empty">No announcements yet.</div>}
      </div>

      {canPost && mine.length > 0 && (
        <div className="card mt-16" style={{ padding: 0 }}>
          <div className="card-title" style={{ padding: "12px 16px" }}>Manage posts</div>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Title</th><th>Audience</th><th>Class</th><th>Posted</th><th></th></tr></thead>
              <tbody>
                {mine.map((a) => (
                  <tr key={a.id}>
                    <td>{a.title}</td><td>{a.audience}</td><td>{a.student_class || "All"}</td>
                    <td>{fmtDate(a.created_at)}</td>
                    <td className="num">
                      <button className="btn btn-danger" style={{ padding: "4px 10px", fontSize: 12 }}
                              onClick={() => remove(a.id)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function NewAnnouncement({ role, onPosted }) {
  const [f, setF] = useState({ title: "", body: "", audience: "all", student_class: "", notify: false });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const post = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      await api.post("/announcements", {
        title: f.title, body: f.body, audience: f.audience,
        student_class: f.student_class || null, notify: f.notify,
      });
      setF({ title: "", body: "", audience: "all", student_class: "", notify: false });
      onPosted();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to post");
    } finally { setBusy(false); }
  };

  return (
    <form className="card mb-16" style={{ padding: 14 }} onSubmit={post}>
      <div className="card-title" style={{ marginBottom: 10 }}>New announcement</div>
      {err && <div className="error-banner">{err}</div>}
      <div className="form-row">
        <input className="input" placeholder="Title" value={f.title} onChange={set("title")} required />
      </div>
      <div className="form-row">
        <textarea className="input" rows={3} placeholder="Message…" value={f.body} onChange={set("body")} required />
      </div>
      <div className="flex gap-12 items-center flex-wrap">
        <select className="select" value={f.audience} onChange={set("audience")}>
          {AUDIENCES.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <select className="select" value={f.student_class} onChange={set("student_class")}>
          <option value="">All classes</option>
          {CLASS_ORDER.map((c) => <option key={c} value={c}>Class {c}</option>)}
        </select>
        <label className="text-2" style={{ fontSize: 13 }}>
          <input type="checkbox" checked={f.notify}
                 onChange={(e) => setF({ ...f, notify: e.target.checked })} />
          {" "}Email this class too
        </label>
        <button className="btn" disabled={busy}>{busy ? "Posting…" : "Post"}</button>
      </div>
    </form>
  );
}
