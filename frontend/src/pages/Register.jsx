import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/apiClient";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import { EclipseGlow } from "@/components/effects/EclipseGlow";
import { BrandLogo } from "@/components/layout/BrandLogo";

// Mirrors backend/app/schemas/auth.py::LabAdminRegister exactly.
const schema = z.object({
  laboratory_code: z.string().min(1, "Required"),
  laboratory_name: z.string().min(1, "Required"),
  registration_number: z.string().optional(),
  address: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  pincode: z.string().optional(),
  country: z.string().optional(),
  phone: z.string().optional(),
  laboratory_email: z.string().email("Enter a valid email").optional().or(z.literal("")),
  website: z.string().optional(),
  accreditation_fields: z.string().optional(),

  first_name: z.string().min(1, "Required"),
  last_name: z.string().optional(),
  email: z.string().email("Enter a valid email"),
  admin_phone: z.string().optional(),
  password: z.string().min(6, "At least 6 characters"),
  designation: z.string().optional(),
  qualification: z.string().optional(),
});

const FIELD_GROUPS = [
  {
    legend: "Laboratory details",
    fields: [
      ["laboratory_code", "Laboratory code"],
      ["laboratory_name", "Laboratory name"],
      ["registration_number", "Registration number"],
      ["accreditation_fields", "Accreditation details"],
    ],
  },
  {
    legend: "Address",
    fields: [
      ["address", "Address"],
      ["city", "City"],
      ["state", "State"],
      ["pincode", "Pincode"],
      ["country", "Country"],
    ],
  },
  {
    legend: "Laboratory contact",
    fields: [
      ["phone", "Laboratory phone"],
      ["laboratory_email", "Laboratory email"],
      ["website", "Website"],
    ],
  },
];

export default function Register() {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const [formError, setFormError] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema), defaultValues: { country: "India" } });

  async function onSubmit(values) {
    setFormError("");
    try {
      // Strip empty-string optionals so they land as null, not "".
      const payload = Object.fromEntries(
        Object.entries(values).map(([k, v]) => [k, v === "" ? undefined : v])
      );
      await api.register(payload);
    } catch (err) {
      setFormError(err.message);
      return;
    }

    // Registration doesn't return a token — log in right after with the
    // same credentials so the new admin lands straight in the dashboard.
    const { error } = await signIn(values.email, values.password);
    if (error) {
      // Account was created fine; just send them to log in manually.
      navigate("/login");
      return;
    }
    navigate("/app/dashboard");
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 py-12">
      <EclipseGlow />
      <div className="relative w-full max-w-2xl rounded-2xl border border-border bg-surface p-8 shadow-raised">
        <BrandLogo className="mb-6" />
        <h1 className="text-xl font-semibold">Register your laboratory</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          This creates your laboratory record and its first lab-admin account.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-6">
          {FIELD_GROUPS.map((group) => (
            <fieldset key={group.legend}>
              <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {group.legend}
              </legend>
              <div className="grid gap-3 sm:grid-cols-2">
                {group.fields.map(([key, label]) => (
                  <div key={key}>
                    <label className="text-sm font-medium">{label}</label>
                    <input
                      {...register(key)}
                      className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                    />
                    {errors[key] && <p className="mt-1 text-xs text-status-fail">{errors[key].message}</p>}
                  </div>
                ))}
              </div>
            </fieldset>
          ))}

          <fieldset>
            <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Lab admin account (you)
            </legend>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="text-sm font-medium">First name</label>
                <input {...register("first_name")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                {errors.first_name && <p className="mt-1 text-xs text-status-fail">{errors.first_name.message}</p>}
              </div>
              <div>
                <label className="text-sm font-medium">Last name</label>
                <input {...register("last_name")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="text-sm font-medium">Email</label>
                <input type="email" {...register("email")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                {errors.email && <p className="mt-1 text-xs text-status-fail">{errors.email.message}</p>}
              </div>
              <div>
                <label className="text-sm font-medium">Phone</label>
                <input {...register("admin_phone")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="text-sm font-medium">Designation</label>
                <input {...register("designation")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="text-sm font-medium">Qualification</label>
                <input {...register("qualification")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="text-sm font-medium">Password</label>
                <input type="password" {...register("password")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                {errors.password && <p className="mt-1 text-xs text-status-fail">{errors.password.message}</p>}
              </div>
            </div>
          </fieldset>

          {formError && <p className="text-xs text-status-fail">{formError}</p>}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Registering…" : "Register laboratory"}
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Already registered?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Login instead
          </Link>
        </p>
      </div>
    </div>
  );
}
