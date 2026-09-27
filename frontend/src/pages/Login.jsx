import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Scale, FlaskConical } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { DEMO_CREDENTIALS } from "@/lib/devAuth";
import { Button } from "@/components/ui/Button";
import { EclipseGlow } from "@/components/effects/EclipseGlow";
import { BrandLogo } from "@/components/layout/BrandLogo";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(6, "At least 6 characters"),
});

export default function Login() {
  const navigate = useNavigate();
  const { signIn, devMode } = useAuth();
  const [formError, setFormError] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) });

  async function onSubmit(values) {
    setFormError("");
    // signIn() checks isDevMode() internally — this call becomes a real
    // Supabase sign-in automatically once .env has real project values,
    // no change needed here. See src/hooks/useAuth.jsx.
    const { error } = await signIn(values.email, values.password);
    if (error) {
      setFormError(error.message);
      return;
    }
    navigate("/app/dashboard");
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4">
      <EclipseGlow />
      <div className="relative w-full max-w-sm rounded-2xl border border-border bg-surface p-8 shadow-raised">
        <BrandLogo className="mb-6" />
        <h1 className="text-xl font-semibold">Login to your lab</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Use the credentials your lab admin created for you.
        </p>

        {devMode && (
          <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-accent/30 bg-accent/10 p-3 text-xs text-accent-foreground">
            <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
            <div>
              <p className="font-medium">No Supabase project connected yet — using a temporary demo login.</p>
              <p className="mt-1 font-num">
                {DEMO_CREDENTIALS.email} / {DEMO_CREDENTIALS.password}
              </p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
          <div>
            <label className="text-sm font-medium">Email</label>
            <input
              type="email"
              {...register("email")}
              className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              placeholder="you@lab.gov.in"
            />
            {errors.email && <p className="mt-1 text-xs text-status-fail">{errors.email.message}</p>}
          </div>
          <div>
            <label className="text-sm font-medium">Password</label>
            <input
              type="password"
              {...register("password")}
              className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              placeholder="••••••••"
            />
            {errors.password && <p className="mt-1 text-xs text-status-fail">{errors.password.message}</p>}
          </div>
          {formError && <p className="text-xs text-status-fail">{formError}</p>}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          New lab?{" "}
          <Link to="/register" className="font-medium text-primary hover:underline">
            Register your laboratory
          </Link>
        </p>
      </div>
    </div>
  );
}
