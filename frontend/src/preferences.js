// Local-only display preferences. Stored in localStorage and applied via
// data-* attributes on <html> so CSS can react.

const KEYS = {
  compact:    "sage_compact",
  fontSize:   "sage_fontsize",
  notifyMail: "sage_notify_mail",
};

export function getPref(key, fallback) {
  const v = localStorage.getItem(key);
  if (v === null) return fallback;
  if (v === "true")  return true;
  if (v === "false") return false;
  return v;
}

export function setPref(key, value) {
  localStorage.setItem(key, String(value));
  apply();
}

export function apply() {
  const root = document.documentElement;
  root.dataset.compact   = String(getPref(KEYS.compact, false));
  root.dataset.fontsize  = getPref(KEYS.fontSize, "normal");
}

export const PREF_KEYS = KEYS;
