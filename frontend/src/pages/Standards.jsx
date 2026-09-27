import React from "react";
import { BookMarked } from "lucide-react";
import { PlaceholderPage } from "@/components/layout/PlaceholderPage";

export default function Standards() {
  return (
    <PlaceholderPage
      icon={BookMarked}
      title="Standards & Rules — next build phase"
      description="Admin reference-data management for standards, test definitions, applicability rules and MPE rules."
      schemaNote="Backed by standards, test_definitions, test_applicability_rules, mpe_rules."
    />
  );
}
