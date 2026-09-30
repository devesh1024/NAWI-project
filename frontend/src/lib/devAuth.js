// The demo account is a REAL row in the backend database (seeded once via
// POST /api/auth/register — see backend/README or ask the backend owner),
// not a frontend bypass. Keeping it means judges/testers can log in without
// registering their own lab. If these credentials ever change on the
// backend, update them here to match — that's the only thing this file does.
export const DEMO_CREDENTIALS = {
  email: "demo@nawitest.com",
  password: "demo1234",
};
