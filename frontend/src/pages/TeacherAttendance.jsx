import React, { useEffect, useState } from "react";
import { api } from "../api";
import AttendanceSheet from "../components/AttendanceSheet";

export default function TeacherAttendance() {
  const [classes, setClasses] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/teacher/me/classes")
      .then((r) => setClasses(r.data.map((c) => c.student_class)))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load your classes"));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Attendance</h1>
          <p className="page-sub">Mark daily or period-wise attendance for your classes.</p>
        </div>
      </div>
      {err && <div className="error-banner">{err}</div>}
      {classes && classes.length === 0 && (
        <div className="card" style={{ padding: 16 }}>You have no classes assigned yet.</div>
      )}
      {classes && classes.length > 0 && <AttendanceSheet classes={classes} />}
    </div>
  );
}
