import React, { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { isDevMode, devSignIn, devSignOut, getDevSession } from "@/lib/devAuth";

const AuthContext = createContext(null);

// ---------------------------------------------------------------------
// TEMPORARY: this whole file switches between real Supabase auth and the
// hardcoded dev user based on isDevMode() (see src/lib/devAuth.js). Once
// a real Supabase project is connected (VITE_SUPABASE_URL set in .env),
// isDevMode() flips to false automatically and every call below routes
// to the real supabase.auth methods instead — no other file needs to
// change. To remove the dev path entirely later: delete devAuth.js and
// the `devMode ? ... : ...` branches below.
// ---------------------------------------------------------------------

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const devMode = isDevMode();

  useEffect(() => {
    if (devMode) {
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

    return () => listener.subscription.unsubscribe();
  }, [devMode]);

  async function signIn(email, password) {
    if (devMode) {
      const result = devSignIn(email, password);
      if (result.error) return result;
      setSession(result.session);
      return result;
    }
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (!error) setSession(data.session);
    return { error };
  }

  function signOut() {
    if (devMode) {
      devSignOut();
      setSession(null);
      return;
    }
    return supabase.auth.signOut();
  }

  const value = {
    session,
    user: session?.user ?? null,
    loading,
    devMode,
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
