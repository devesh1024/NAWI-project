import React from "react";
import { ScrollText } from "lucide-react";
import { PlaceholderPage } from "@/components/layout/PlaceholderPage";

export default function AuditLog() {
  return (
    <PlaceholderPage
      icon={ScrollText}
      title="Audit log — next build phase"
      description="Filterable, timestamped activity feed: create/update/delete/import/submit/approve/reject/generate/download/login."
      schemaNote="Backed by audit_logs."
    />
  );
}
