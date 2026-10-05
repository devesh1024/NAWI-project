// The demo account is a REAL row in the backend database (seeded once via
// POST /api/auth/register — see backend/README or ask the backend owner),
// not a frontend bypass. Keeping it means judges/testers can log in without
// registering their own lab. If these credentials ever change on the
// backend, update them here to match — that's the only thing this file does.
export const DEMO_CREDENTIALS = {
  email: "demo@nawitest.com",
  password: "demo1234",
};

// One demo account per laboratory role, all in the same demo lab, so each
// role's screens can be explored. Created by `python -m backend.seed_demo_lab`
// (the Lab Head above is the first of them). Password is the same for all.
export const DEMO_ROLES = [
  { role: "Lab Head / In-charge", email: "demo@nawitest.com" },
  { role: "Technical Manager", email: "tm@nawitest.com" },
  { role: "Quality Manager", email: "quality@nawitest.com" },
  { role: "Reviewer", email: "reviewer@nawitest.com" },
  { role: "Authorised Signatory", email: "signatory@nawitest.com" },
  { role: "Senior Tester / Evaluator", email: "tester@nawitest.com" },
  { role: "Technician / Lab Assistant", email: "assistant@nawitest.com" },
  { role: "Receiving / Records Officer", email: "records@nawitest.com" },
  { role: "Standards Custodian", email: "custodian@nawitest.com" },
  { role: "Auditor (read-only)", email: "auditor@nawitest.com" },
];
