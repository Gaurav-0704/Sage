import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";

/** Redirects users without the right role to "/" */
export default function RoleRoute({ role, children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to="/" replace />;
  return children;
}
