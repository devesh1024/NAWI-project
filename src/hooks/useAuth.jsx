import React, { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { isDevMode, devSignOut, getDevSession, devSignIn } from "@/lib/devAuth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isDevMode()) {
      setSession(getDevSession());
      setLoading(false);
      return;
    }

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => listener?.subscription?.unsubscribe();
  }, []);

  const value = {
    session,
    user: session?.user ?? null,
    loading,
    signIn: async ({ email, password }) => {
      if (isDevMode()) {
        const result = devSignIn(email, password);
        if (!result.error) {
          setSession(result.session);
        }
        return result;
      }
      return supabase.auth.signInWithPassword({ email, password });
    },
    signOut: () => {
      if (isDevMode()) {
        devSignOut();
        setSession(null);
      } else {
        supabase.auth.signOut();
      }
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
