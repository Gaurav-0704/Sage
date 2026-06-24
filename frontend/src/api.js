import axios from "axios";

// Build-time API base. The API is served under /api.
//  - single-service (FastAPI serves the build): REACT_APP_API_BASE="/api"
//  - two-service: REACT_APP_API_BASE="https://your-backend.up.railway.app/api"
//  - local `npm start`: defaults to the local dev server below.
export const API_BASE = process.env.REACT_APP_API_BASE || "http://127.0.0.1:8000/api";

export const TOKEN_KEY = "sage_token";
export const USER_KEY  = "sage_user";

export const api = axios.create({ baseURL: API_BASE });

// Attach JWT on every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401 anywhere, clear the session.
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
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
