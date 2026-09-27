import React from "react";
import { Settings as SettingsIcon } from "lucide-react";
import { PlaceholderPage } from "@/components/layout/PlaceholderPage";

export default function Settings() {
  return (
    <PlaceholderPage
      icon={SettingsIcon}
      title="Settings — next build phase"
      description="Profile details and laboratory preferences."
    />
  );
}
