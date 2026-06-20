import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate } from "../api";
import { useAuth } from "../auth";
import CredentialsCard from "../components/CredentialsCard";

export default function TeacherDashboard() {
  const { user } = useAuth();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/teacher/me/dashboard")
      .then((r) => setD(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Welcome, {user?.name?.split(" ")[0]}</h1>
          <p className="page-sub">Your classes and assignments at a glance.</p>
        </div>
        <span className="pill indigo">Teacher</span>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <CredentialsCard/>

      {d && (
        <>
          <div className="grid grid-cols-3 mb-16">
            <div className="card stat">
              <div className="label">Classes I teach</div>
              <div className="value">{d.classes.length}</div>
              <div className="delta">{d.classes.join(", ") || "—"}</div>
            </div>
            <div className="card stat">
              <div className="label">Students</div>
              <div className="value">{d.students_count}</div>
              <div className="delta">across all your classes</div>
            </div>
            <div className="card stat">
              <div className="label">Active assignments</div>
              <div className="value">{d.assignments_count}</div>
              <div className="delta">click below to manage</div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">
              Upcoming due
              <Link to="/assignments" style={{ fontSize: 12 }}>Manage all →</Link>
            </div>
            {d.upcoming_due.length === 0 ? (
              <div className="empty">No upcoming assignments.</div>
            ) : (
              <table className="table">
                <thead>
                  <tr><th>Title</th><th>Class</th><th>Subject</th><th>Due</th><th className="num">Max marks</th></tr>
                </thead>
                <tbody>
                  {d.upcoming_due.map((a) => (
                    <tr key={a.id}>
                      <td style={{ fontWeight: 500 }}>{a.title}</td>
                      <td>{a.student_class}{a.section ? `-${a.section}` : ""}</td>
                      <td>{a.subject}</td>
                      <td>{fmtDate(a.due_date)}</td>
                      <td className="num">{a.max_marks}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
