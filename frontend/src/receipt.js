import { api } from "./api";

/**
 * Pop a printable receipt for any kind of transaction in a new window.
 * The window auto-triggers the browser's print dialog, where the user can
 * pick a real printer or "Save as PDF" from the destination dropdown.
 *
 * Supported kinds: "payment" (fee receipt) and "expense" (voucher).
 */
export async function openReceipt(kindOrId, maybeId) {
  // Backwards compatibility: openReceipt(paymentId) used to work.
  let kind, id;
  if (maybeId === undefined) { kind = "payment"; id = kindOrId; }
  else                        { kind = kindOrId; id = maybeId; }

  const path = kind === "expense"
    ? `/expenses/${id}/receipt`
    : `/payments/${id}/receipt`;

  try {
    const res = await api.get(path, { responseType: "text" });
    const w = window.open("", "_blank", "width=520,height=720");
    if (!w) {
      alert("Receipt blocked by your browser pop-up settings. Allow popups for "
            + window.location.host + " to see receipts.");
      return;
    }
    w.document.open();
    w.document.write(res.data);
    w.document.close();
  } catch (e) {
    alert("Couldn't load receipt: " + (e?.response?.data?.detail || e.message));
  }
}
