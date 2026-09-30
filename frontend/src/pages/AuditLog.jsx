import React from "react";
import { ScrollText } from "lucide-react";
import { PlaceholderPage } from "@/components/layout/PlaceholderPage";

// The audit_logs table exists and IS being written to — reports/routes.py
// calls create_audit_log() on report generation/approval. What's missing is
// a GET endpoint to read them back. This page can go live as soon as a
// GET /api/audit-logs (or similar) route exists — no other blocker.
export default function AuditLog() {
  return (
    <PlaceholderPage
      icon={ScrollText}
      title="Audit log — waiting on a read endpoint"
      description="Audit entries are already being recorded server-side (report generation/approval, at minimum). There's just no API route to list them back yet."
      schemaNote="Backed by audit_logs — ask backend for a GET /api/audit-logs endpoint to unblock this page."
    />
  );
}
