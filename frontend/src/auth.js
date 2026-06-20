import React, { createContext, useContext, useState, useCallback } from "react";
import { api } from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("nhs_user");
    return raw ? JSON.parse(raw) : null;
  });

  const login = useCallback(async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    localStorage.setItem("nhs_token", res.data.access_token);
    localStorage.setItem("nhs_user", JSON.stringify(res.data.user));
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("nhs_token");
    localStorage.removeItem("nhs_user");
    setUser(null);
  }, []);

  const isOwner = user?.role === "owner";
  const isStaff = user?.role === "staff";

  return (
    <AuthCtx.Provider value={{ user, login, logout, isOwner, isStaff }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
