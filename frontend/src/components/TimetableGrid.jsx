import React from "react";

export const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/**
 * Read-only weekly grid (periods × days) rendered from a flat entries list.
 * Each entry: { day, period, subject, teacher_name, room }.
 * `maxPeriod` controls how many period rows are shown (defaults to the data).
 */
export default function TimetableGrid({ entries, maxPeriod }) {
  const map = {};
  let hi = 0;
  entries.forEach((e) => {
    map[`${e.day}-${e.period}`] = e;
    if (e.period > hi) hi = e.period;
  });
  const periods = [];
  const top = maxPeriod || Math.max(hi, 6);
  for (let p = 1; p <= top; p++) periods.push(p);

  return (
    <div className="table-wrap">
      <table className="table timetable-grid">
        <thead>
          <tr>
            <th style={{ width: 70 }}>Period</th>
            {DAYS.map((d) => <th key={d}>{d}</th>)}
          </tr>
        </thead>
        <tbody>
          {periods.map((p) => (
            <tr key={p}>
              <td style={{ fontWeight: 600 }}>P{p}</td>
              {DAYS.map((d) => {
                const e = map[`${d}-${p}`];
                return (
                  <td key={d} style={{ verticalAlign: "top" }}>
                    {e ? (
                      <div>
                        <div style={{ fontWeight: 600 }}>{e.subject}</div>
                        {e.teacher_name && <div className="text-2" style={{ fontSize: 12 }}>{e.teacher_name}</div>}
                        {e.room && <div className="text-2" style={{ fontSize: 11 }}>Room {e.room}</div>}
                      </div>
                    ) : <span className="text-2">—</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
