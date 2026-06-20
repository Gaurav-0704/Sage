import axios from "axios";

export const API_BASE = "http://127.0.0.1:8000";

export const api = axios.create({ baseURL: API_BASE });

// Attach JWT on every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("nhs_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401 anywhere, clear the session.
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem("nhs_token");
      localStorage.removeItem("nhs_user");
      if (window.location.pathname !== "/login") window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const fmtINR = (n) =>
  "₹" +
  Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });

export const fmtDate = (d) => {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("en-IN", {
      day: "2-digit", month: "short", year: "numeric",
    });
  } catch { return d; }
};
