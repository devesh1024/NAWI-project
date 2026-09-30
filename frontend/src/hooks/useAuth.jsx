import React, { createContext, useContext, useState } from "react";
import { api } from "@/lib/apiClient";

const AuthContext = createContext(null);
const STORAGE_KEY = "nawi_session";

function readStoredSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readStoredSession);

  async function signIn(email, password) {
    try {
      const data = await api.login({ email, password });
      const newSession = {
        token: data.access_token,
        userId: data.user_id,
        laboratoryId: data.laboratory_id,
        role: data.role,
        email,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newSession));
      setSession(newSession);
      return { session: newSession };
    } catch (err) {
      return { error: { message: err.message } };
    }
  }

  function signOut() {
    localStorage.removeItem(STORAGE_KEY);
    setSession(null);
  }

  const value = {
    session,
    token: session?.token ?? null,
    role: session?.role ?? null,
    email: session?.email ?? null,
    loading: false,
    signIn,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
