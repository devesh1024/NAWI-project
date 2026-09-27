// Dev-only stand-in for Supabase Auth, used automatically whenever
// VITE_SUPABASE_URL isn't set (i.e. no real project connected yet).
// Delete this file once real Supabase auth is wired up — nothing else
// needs it directly except useAuth.jsx and AppShell.jsx.

export const DEMO_CREDENTIALS = {
  email: "demo@nawitest.local",
  password: "demo1234",
};

const DEMO_USER = { id: "demo-user-id", email: DEMO_CREDENTIALS.email };

const DEMO_PROFILE = {
  first_name: "Demo",
  last_name: "Admin",
  role: "lab_admin", // change to "tester" / "reviewer" / "approver" to preview other roles
  laboratory_id: "demo-lab-id",
};

const STORAGE_KEY = "nawi_dev_session";

export function isDevMode() {
  return !import.meta.env.VITE_SUPABASE_URL || import.meta.env.VITE_DEV_MODE === "true";
}

export function devSignIn(email, password) {
  if (email === DEMO_CREDENTIALS.email && password === DEMO_CREDENTIALS.password) {
    localStorage.setItem(STORAGE_KEY, "1");
    return { session: { user: DEMO_USER } };
  }
  return {
    error: { message: `Invalid demo credentials. Use ${DEMO_CREDENTIALS.email} / ${DEMO_CREDENTIALS.password}.` },
  };
}

export function devSignOut() {
  localStorage.removeItem(STORAGE_KEY);
}

export function getDevSession() {
  return localStorage.getItem(STORAGE_KEY) ? { user: DEMO_USER } : null;
}

export function getDevProfile() {
  return DEMO_PROFILE;
}
