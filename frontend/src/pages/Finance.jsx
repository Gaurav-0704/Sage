import React, { useEffect, useState, useCallback } from "react";
import { api, fmtINR } from "../api";
import { useAuth } from "../auth";

export default function Finance() {
  const { isStaff } = useAuth();
  const [s, setS] = useState(null);
  const [err, setErr] = useState("");
  const [edit, setEdit] = useState(null); // "cash" | "bank" | null

  const load = useCallback(() => {
    api.get("/finance/summary")
      .then((r) => setS(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"));
  }, []);

  useEffect(load, [load]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Finance</h1>
          <p className="page-sub">Live balances. Recomputed from payments + expenses, no manual updates.</p>
        </div>
      </div>

      {err && <div className="error-banner">{err}</div>}

      {s && (
        <>
          <div className="grid grid-cols-3 mb-16">
            <div className="card stat">
              <div className="label">Cash on hand</div>
              <div className="value">{fmtINR(s.cash.balance)}</div>
              <div className="delta">opening: {fmtINR(s.cash.opening_balance)}
                {isStaff && <button className="btn btn-secondary" style={{ marginLeft: 8, padding: "2px 8px", fontSize: 11 }}
                                    onClick={() => setEdit("cash")}>edit</button>}
              </div>
            </div>
            <div className="card stat">
              <div className="label">Bank balance</div>
              <div className="value">{fmtINR(s.bank.balance)}</div>
              <div className="delta">opening: {fmtINR(s.bank.opening_balance)}
                {isStaff && <button className="btn btn-secondary" style={{ marginLeft: 8, padding: "2px 8px", fontSize: 11 }}
                                    onClick={() => setEdit("bank")}>edit</button>}
              </div>
            </div>
            <div className="card stat">
              <div className="label">Total available</div>
              <div className="value green">{fmtINR(s.total_balance)}</div>
              <div className="delta">cash + bank</div>
            </div>
          </div>

          <div className="grid grid-cols-2">
            <div className="card">
              <div className="card-title">Today</div>
              <div className="flex between" style={{ padding: "8px 0" }}>
                <div className="text-2">Collected</div>
                <div className="tabular" style={{ fontWeight: 600, color: "var(--green)" }}>
                  {fmtINR(s.total_collected_today)}
                </div>
              </div>
              <div className="flex between" style={{ padding: "8px 0" }}>
                <div className="text-2">Expenses</div>
                <div className="tabular" style={{ fontWeight: 600, color: "var(--red)" }}>
                  {fmtINR(s.total_expense_today)}
                </div>
              </div>
              <div className="flex between" style={{ padding: "8px 0", borderTop: "1px solid var(--border)" }}>
                <div style={{ fontWeight: 600 }}>Net today</div>
                <div className="tabular" style={{ fontWeight: 700 }}>
                  {fmtINR(s.total_collected_today - s.total_expense_today)}
                </div>
              </div>
            </div>
            <div className="card">
              <div className="card-title">This month</div>
              <div className="flex between" style={{ padding: "8px 0" }}>
                <div className="text-2">Collected</div>
                <div className="tabular" style={{ fontWeight: 600, color: "var(--green)" }}>
                  {fmtINR(s.total_collected_month)}
                </div>
              </div>
              <div className="flex between" style={{ padding: "8px 0" }}>
                <div className="text-2">Expenses</div>
                <div className="tabular" style={{ fontWeight: 600, color: "var(--red)" }}>
                  {fmtINR(s.total_expense_month)}
                </div>
              </div>
              <div className="flex between" style={{ padding: "8px 0", borderTop: "1px solid var(--border)" }}>
                <div style={{ fontWeight: 600 }}>Net month</div>
                <div className="tabular" style={{ fontWeight: 700 }}>
                  {fmtINR(s.total_collected_month - s.total_expense_month)}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {edit && (
        <OpeningBalanceModal
          name={edit}
          current={s[edit].opening_balance}
          onClose={() => setEdit(null)}
          onSaved={() => { setEdit(null); load(); }}
        />
      )}
    </div>
  );
}

function OpeningBalanceModal({ name, current, onClose, onSaved }) {
  const [v, setV] = useState(current);
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);

  const save = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      await api.put(`/finance/accounts/${name}`, { opening_balance: Number(v) });
      onSaved();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={save}>
        <h3>Set opening balance — {name}</h3>
        {err && <div className="error-banner">{err}</div>}
        <p className="text-2" style={{ fontSize: 12, marginTop: 0 }}>
          The current balance is recomputed automatically from payments and expenses.
          Changing the opening balance shifts the entire history by this amount.
        </p>
        <div className="form-row">
          <label>Opening balance (₹)</label>
          <input className="input" type="number" value={v} onChange={(e) => setV(e.target.value)}/>
        </div>
        <div className="flex gap-8" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn" disabled={busy}>{busy ? "Saving…" : "Save"}</button>
        </div>
      </form>
    </div>
  );
}
