import React from "react";
import { FileText } from "lucide-react";
import { PlaceholderPage } from "@/components/layout/PlaceholderPage";

export default function Reports() {
  return (
    <PlaceholderPage
      icon={FileText}
      title="Report repository — next build phase"
      description="Searchable, filterable report list with version history, PDF/DOCX download and digital sign-off status."
      schemaNote="Backed by reports, report_versions, digital_signatures."
    />
  );
}
