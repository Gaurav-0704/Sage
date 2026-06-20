import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api";

export default function OwnerScanner() {
  const [runs, setRuns] = useState([]);
  const [active, setActive] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    api.get("/scanner/runs?limit=50")
      .then((r) => {
        setRuns(r.data);
        if (r.data.length && !active) setActive(r.data[0]);
      })
      .catch((e) => setErr(e?.response?.data?.detail || "Failed"));
  }, [active]);
  useEffect(load, []); // eslint-disable-line

  const runNow = async () => {
    setBusy(true); setErr("");
    try {
      const r = await api.post("/scanner/run");
      setActive(r.data);
      load();
    } catch (e) { setErr(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  const findings = active?.findings ? JSON.parse(active.findings) : [];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">System Scanner</h1>
          <p className="page-sub">
            Runs nightly at 02:00. Scans every agent + database table + linter,
            then notifies the Owner.
          </p>
        </div>
        <button className="btn" onClick={runNow} disabled={busy}>
          {busy ? "Scanning…" : "▶ Run scan now"}
        </button>
      </div>

      {err && <div className="error-banner">{err}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 16 }}>
        <div className="card" style={{ padding: 8, maxHeight: "70vh", overflow: "auto" }}>
          {runs.length === 0 && (
            <div className="empty">No scans yet — run one to get started.</div>
          )}
          {runs.map((r) => (
            <button key={r.id} className="roster-row"
                    style={{ background: active?.id === r.id ? "var(--brand-50)" : "transparent",
                             borderRadius: 8 }}
                    onClick={() => setActive(r)}>
              <span className={"pill " + statusPill(r.status)} style={{ marginRight: 8 }}>
                {r.status}
              </span>
              <div style={{ flex: 1, overflow: "hidden" }}>
                <div style={{ fontSize: 12, fontWeight: 500 }}>
                  {new Date(r.started_at).toLocaleString()}
                </div>
                <div className="text-3" style={{ fontSize: 11 }}>
                  {r.triggered_by} · {r.issues_count} issue{r.issues_count !== 1 && "s"}
                </div>
              </div>
            </button>
          ))}
        </div>

        <div>
          {!active ? (
            <div className="card empty">Pick a scan from the list.</div>
          ) : (
            <>
              <div className="card mb-16">
                <div className="grid grid-cols-3">
                  <Stat label="Status" value={active.status} pill={statusPill(active.status)}/>
                  <Stat label="Triggered by" value={active.triggered_by}/>
                  <Stat label="Issues found" value={active.issues_count}/>
                </div>
                <div className="text-2" style={{ marginTop: 12, fontSize: 13 }}>
                  {active.summary}
                </div>
              </div>

              <div className="card">
                <div className="card-title">Findings ({findings.length})</div>
                {findings.length === 0 ? (
                  <div className="empty" style={{ color: "var(--green)" }}>
                    🎉 No issues detected.
                  </div>
                ) : (
                  <table className="table">
                    <thead>
                      <tr><th>Severity</th><th>Category</th><th>Where</th><th>Detail</th></tr>
                    </thead>
                    <tbody>
                      {findings.map((f, i) => (
                        <tr key={i}>
                          <td><span className={"pill " + (f.severity === "error" ? "red" : "amber")}>
                            {f.severity}
                          </span></td>
                          <td>{f.category}</td>
                          <td className="tabular" style={{ fontSize: 12 }}>{f.where}</td>
                          <td className="text-2" style={{ fontSize: 12 }}>{f.detail}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, pill }) {
  return (
    <div className="card stat" style={{ padding: 14 }}>
      <div className="label">{label}</div>
      <div className="value" style={{ fontSize: 18 }}>
        {pill ? <span className={"pill " + pill}>{value}</span> : value}
      </div>
    </div>
  );
}

function statusPill(s) {
  return { ok: "green", issues: "amber", failed: "red", running: "indigo" }[s] || "";
}
