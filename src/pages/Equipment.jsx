import React from "react";
import { Wrench } from "lucide-react";
import { PlaceholderPage } from "@/components/layout/PlaceholderPage";

export default function Equipment() {
  return (
    <PlaceholderPage
      icon={Wrench}
      title="Equipment — next build phase"
      description="Lab test equipment with calibration status (valid / due-soon / overdue) and certificate references."
      schemaNote="Backed by test_equipment, test_equipment_usage."
    />
  );
}
