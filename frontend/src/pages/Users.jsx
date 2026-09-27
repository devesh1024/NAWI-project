import React from "react";
import { Users2 } from "lucide-react";
import { PlaceholderPage } from "@/components/layout/PlaceholderPage";

export default function Users() {
  return (
    <PlaceholderPage
      icon={Users2}
      title="Users — next build phase"
      description="Lab admin manages testers/reviewers/approvers, roles and authorization scope for this laboratory only."
      schemaNote="Backed by users, scoped by laboratory_id via Row-Level Security."
    />
  );
}
