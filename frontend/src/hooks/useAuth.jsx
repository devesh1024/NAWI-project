import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/apiClient";
import { roleLabel } from "@/lib/roles";

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
  // The signed-in person's profile, including their role and what it allows.
  // Loaded from the server (not the login token) so a role the Lab Head changes
  // takes effect straight away.
  const [profile, setProfile] = useState(null);

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
      setProfile(null);
      setSession(newSession);
      return { session: newSession };
    } catch (err) {
      return { error: { message: err.message } };
    }
  }

  const signOut = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setProfile(null);
    setSession(null);
  }, []);

  const token = session?.token ?? null;

  const refreshProfile = useCallback(async () => {
    if (!token) return null;
    try {
      const me = await api.getMyProfile(token);
      setProfile(me);
      return me;
    } catch (err) {
      // An expired token or a deactivated account: back to the login screen.
      if (/expired|invalid|not active|credentials|401|403/i.test(err.message)) signOut();
      return null;
    }
  }, [token, signOut]);

  useEffect(() => {
    if (token) refreshProfile();
  }, [token, refreshProfile]);

  const value = useMemo(() => {
    const capabilities = new Set(profile?.capabilities ?? []);
    const role = profile?.role ?? session?.role ?? null;
    const name = profile
      ? [profile.first_name, profile.last_name].filter(Boolean).join(" ") || profile.email
      : null;

    return {
      session,
      token,
      role,
      roleLabel: profile?.role_label ?? roleLabel(role),
      email: session?.email ?? null,
      profile,
      name,
      profileReady: !!profile,
      // can("sessions.review"): true when the signed-in role holds that permission.
      can: (capability) => capabilities.has(capability),
      refreshProfile,
      loading: false,
      signIn,
      signOut,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, profile, token, refreshProfile, signOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
