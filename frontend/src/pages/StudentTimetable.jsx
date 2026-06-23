import React, { useEffect, useState } from "react";
import { api } from "../api";
import TimetableGrid from "../components/TimetableGrid";

export default function StudentTimetable() {
  const [entries, setEntries] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/student/me/timetable")
      .then((r) => setEntries(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load timetable"));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">My Timetable</h1>
          <p className="page-sub">Your class's weekly schedule.</p>
        </div>
      </div>
      {err && <div className="error-banner">{err}</div>}
      <TimetableGrid entries={entries} />
    </div>
  );
}
