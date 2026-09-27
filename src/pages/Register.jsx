import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Scale } from "lucide-react";
import { supabase } from "@/lib/supabaseClient";
import { Button } from "@/components/ui/Button";
import { EclipseGlow } from "@/components/effects/EclipseGlow";
import { BrandLogo } from "@/components/layout/BrandLogo";

// Mirrors the `laboratories` table + the lab_admin `users` row created alongside it.
const schema = z.object({
  name: z.string().min(2, "Required"),
  registration_number: z.string().min(1, "Required"),
  address_line_1: z.string().min(1, "Required"),
  address_line_2: z.string().optional(),
  city: z.string().min(1, "Required"),
  state: z.string().min(1, "Required"),
  pincode: z.string().min(4, "Required"),
  country: z.string().min(1, "Required").default("India"),
  phone: z.string().min(6, "Required"),
  email: z.string().email("Enter a valid lab email"),
  accreditation_body: z.string().optional(),
  accreditation_number: z.string().optional(),
  admin_first_name: z.string().min(1, "Required"),
  admin_last_name: z.string().min(1, "Required"),
  admin_email: z.string().email("Enter a valid email"),
  admin_password: z.string().min(6, "At least 6 characters"),
});

const FIELD_GROUPS = [
  {
    legend: "Laboratory details",
    fields: [
      ["name", "Laboratory name"],
      ["registration_number", "Registration number"],
      ["accreditation_body", "Accreditation body (optional)"],
      ["accreditation_number", "Accreditation number (optional)"],
    ],
  },
  {
    legend: "Address",
    fields: [
      ["address_line_1", "Address line 1"],
      ["address_line_2", "Address line 2 (optional)"],
      ["city", "City"],
      ["state", "State"],
      ["pincode", "Pincode"],
      ["country", "Country"],
    ],
  },
  {
    legend: "Contact",
    fields: [
      ["phone", "Laboratory phone"],
      ["email", "Laboratory email"],
    ],
  },
];

export default function Register() {
  const navigate = useNavigate();
  const [formError, setFormError] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema), defaultValues: { country: "India" } });

  async function onSubmit(values) {
    setFormError("");

    // 1. Create the auth user (becomes the lab_admin).
    const { data: signUpData, error: signUpError } = await supabase.auth.signUp({
      email: values.admin_email,
      password: values.admin_password,
    });
    if (signUpError) {
      setFormError(signUpError.message);
      return;
    }

    // 2. Create the laboratory row.
    const { data: lab, error: labError } = await supabase
      .from("laboratories")
      .insert({
        name: values.name,
        registration_number: values.registration_number,
        address_line_1: values.address_line_1,
        address_line_2: values.address_line_2 || null,
        city: values.city,
        state: values.state,
        pincode: values.pincode,
        country: values.country,
        phone: values.phone,
        email: values.email,
        accreditation_body: values.accreditation_body || null,
        accreditation_number: values.accreditation_number || null,
        status: "pending_verification",
      })
      .select()
      .single();
    if (labError) {
      setFormError(labError.message);
      return;
    }

    // 3. Create the users row linking the auth user to this lab as lab_admin.
    const { error: userError } = await supabase.from("users").insert({
      user_id: signUpData.user.id,
      laboratory_id: lab.laboratory_id,
      first_name: values.admin_first_name,
      last_name: values.admin_last_name,
      email: values.admin_email,
      role: "lab_admin",
      status: "active",
    });
    if (userError) {
      setFormError(userError.message);
      return;
    }

    navigate("/login");
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
                <input {...register("admin_first_name")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                {errors.admin_first_name && <p className="mt-1 text-xs text-status-fail">{errors.admin_first_name.message}</p>}
              </div>
              <div>
                <label className="text-sm font-medium">Last name</label>
                <input {...register("admin_last_name")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                {errors.admin_last_name && <p className="mt-1 text-xs text-status-fail">{errors.admin_last_name.message}</p>}
              </div>
              <div>
                <label className="text-sm font-medium">Email</label>
                <input type="email" {...register("admin_email")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                {errors.admin_email && <p className="mt-1 text-xs text-status-fail">{errors.admin_email.message}</p>}
              </div>
              <div>
                <label className="text-sm font-medium">Password</label>
                <input type="password" {...register("admin_password")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                {errors.admin_password && <p className="mt-1 text-xs text-status-fail">{errors.admin_password.message}</p>}
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
