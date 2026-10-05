// Roles, in one place.
//
// The backend (backend/app/services/permissions.py) is the source of truth for
// what each role may do and it enforces it on every request. This file only
// holds the presentation side: names, colours, and which screens each role
// needs, so the interface a person sees matches their job.

export const ROLE_LABELS = {
  LAB_ADMIN: "Lab Head / In-charge",
  TECHNICAL_MANAGER: "Technical Manager",
  QUALITY_MANAGER: "Quality Manager",
  REVIEWER: "Reviewer",
  APPROVER: "Authorised Signatory",
  TESTER: "Senior Tester / Evaluator",
  ASSISTANT: "Technician / Lab Assistant",
  RECORDS_OFFICER: "Receiving / Records Officer",
  STANDARDS_CUSTODIAN: "Standards Custodian",
  AUDITOR: "Auditor (read-only)",
};

export function roleLabel(role) {
  if (!role) return "";
  if (ROLE_LABELS[role]) return ROLE_LABELS[role];
  const words = String(role).toLowerCase().replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// Chip colours per level of the laboratory, drawn from the site theme.
const GROUP_TONES = {
  Management: "bg-primary/10 text-primary ring-1 ring-primary/25",
  Technical: "bg-accent/15 text-accent-foreground ring-1 ring-accent/30",
  Support: "bg-status-na/10 text-status-na ring-1 ring-status-na/25",
  External: "bg-muted text-muted-foreground ring-1 ring-border",
};

const ROLE_GROUP = {
  LAB_ADMIN: "Management",
  TECHNICAL_MANAGER: "Management",
  QUALITY_MANAGER: "Management",
  REVIEWER: "Technical",
  APPROVER: "Technical",
  TESTER: "Technical",
  ASSISTANT: "Technical",
  RECORDS_OFFICER: "Support",
  STANDARDS_CUSTODIAN: "Support",
  AUDITOR: "External",
};

export const roleTone = (role) => GROUP_TONES[ROLE_GROUP[role]] || GROUP_TONES.External;

// Which screens each role actually works in. Everyone gets the dashboard,
// instruments (to read) and equipment (to read).
const SESSION_ROLES = [
  "LAB_ADMIN", "TECHNICAL_MANAGER", "QUALITY_MANAGER", "REVIEWER",
  "APPROVER", "TESTER", "ASSISTANT", "AUDITOR",
];
const REPORT_ROLES = [
  "LAB_ADMIN", "TECHNICAL_MANAGER", "QUALITY_MANAGER", "REVIEWER",
  "APPROVER", "TESTER", "AUDITOR",
];
const METHOD_ROLES = ["LAB_ADMIN", "TECHNICAL_MANAGER", "QUALITY_MANAGER", "REVIEWER", "AUDITOR"];

export const ROUTE_ACCESS = {
  dashboard: () => true,
  instruments: () => true,
  equipment: () => true,
  "test-sessions": (me) => SESSION_ROLES.includes(me.role),
  reports: (me) => REPORT_ROLES.includes(me.role),
  standards: (me) => METHOD_ROLES.includes(me.role),
  users: (me) => me.can("users.view"),
  "audit-log": (me) => me.can("audit.view"),
  settings: () => true,
};

export const canOpen = (me, key) => (ROUTE_ACCESS[key] ? ROUTE_ACCESS[key](me) : true);

// One-line explanation of the workflow stage, shown next to a session's status.
export const STATUS_HELP = {
  DRAFT: "Planned by the tester. Testing has not started.",
  "IN PROGRESS": "The tester is testing. Data can still change.",
  SUBMITTED: "Handed over. Waiting for a reviewer to pick it up.",
  "UNDER REVIEW": "A reviewer is checking the work and report.",
  APPROVED: "Signed off. Final and locked.",
  REJECTED: "Sent back to the tester for correction.",
};

export const STATUS_LABEL = {
  DRAFT: "Draft",
  "IN PROGRESS": "In progress",
  SUBMITTED: "Submitted",
  "UNDER REVIEW": "Under review",
  APPROVED: "Approved",
  REJECTED: "Returned",
};

// Plain-language names for the permissions a role carries.
export const CAPABILITY_TEXT = {
  "users.view": "See the staff list",
  "users.manage": "Add staff and change roles",
  "users.authorize": "Authorise testers for specific tests",
  "lab.manage": "Edit the laboratory profile",
  "instruments.register": "Receive and record instruments",
  "instruments.delete": "Delete instrument records",
  "equipment.manage": "Keep reference weights and calibration",
  "equipment.delete": "Delete equipment records",
  "methods.manage": "Manage standards, test methods and MPE rules",
  "sessions.create": "Plan test sessions and tests",
  "sessions.enter_data": "Record readings and conditions",
  "sessions.calculate": "Run calculations",
  "sessions.submit": "Submit work for review",
  "sessions.review": "Review work and reports",
  "sessions.approve": "Sign: approve or reject reports",
  "reports.generate": "Draft and regenerate reports",
  "reports.delete": "Delete reports",
  "audit.view": "Read the audit trail",
};

// Permissions in the order they matter, not alphabetical.
export const sortCapabilities = (list = []) => {
  const order = Object.keys(CAPABILITY_TEXT);
  return [...list].sort((a, b) => order.indexOf(a) - order.indexOf(b));
};
