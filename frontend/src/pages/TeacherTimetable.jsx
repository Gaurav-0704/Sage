import React, { useEffect, useState } from "react";
import { api } from "../api";
import TimetableGrid from "../components/TimetableGrid";

export default function TeacherTimetable() {
  const [entries, setEntries] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/timetable/teacher/me")
      .then((r) => setEntries(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load timetable"));
  }, []);

  // Show class+section in the cell since this spans the teacher's classes.
  const decorated = entries.map((e) => ({
    ...e,
    teacher_name: `${e.student_class}-${e.section}${e.room ? "" : ""}`,
  }));

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">My Timetable</h1>
          <p className="page-sub">Your weekly teaching schedule across all classes.</p>
        </div>
      </div>
      {err && <div className="error-banner">{err}</div>}
      <TimetableGrid entries={decorated} />
    </div>
  );
}
