import React from "react";
import { Card, CardContent } from "@/components/ui/Card";

export function PlaceholderPage({ icon: Icon, title, description, schemaNote }) {
  return (
    <div className="flex h-full min-h-[60vh] items-center justify-center">
      <Card className="max-w-md text-center">
        <CardContent className="pt-8">
          {Icon && (
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Icon className="h-6 w-6" />
            </div>
          )}
          <h2 className="font-heading text-lg font-semibold">{title}</h2>
          <p className="mt-2 text-sm text-muted-foreground">{description}</p>
          {schemaNote && (
            <p className="mt-3 rounded-lg bg-muted px-3 py-2 text-xs text-muted-foreground">
              {schemaNote}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
