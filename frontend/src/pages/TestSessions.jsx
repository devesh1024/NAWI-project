import React from "react";
import { FlaskConical } from "lucide-react";
import { PlaceholderPage } from "@/components/layout/PlaceholderPage";

export default function TestSessions() {
  return (
    <PlaceholderPage
      icon={FlaskConical}
      title="Test session wizard — next build phase"
      description="The 6-step flow (select instrument → applicability check → environment → observations/import → calculated results → submit) lands here."
      schemaNote="Backed by test_sessions, test_session_tests, test_observations, test_calculations, test_results."
    />
  );
}
