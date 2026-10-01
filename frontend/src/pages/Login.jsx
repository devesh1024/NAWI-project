import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { FlaskConical, ArrowLeft } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { DEMO_CREDENTIALS } from "@/lib/devAuth";
import { Button } from "@/components/ui/Button";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { EclipseGlow } from "@/components/effects/EclipseGlow";
import { BrandLogo } from "@/components/layout/BrandLogo";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Required"),
});

export default function Login() {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const [formError, setFormError] = useState("");
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) });

  async function onSubmit(values) {
    setFormError("");
    const { error } = await signIn(values.email, values.password);
    if (error) {
      setFormError(error.message);
      return;
    }
    navigate("/app/dashboard");
  }

  function fillDemoCredentials() {
    setValue("email", DEMO_CREDENTIALS.email);
    setValue("password", DEMO_CREDENTIALS.password);
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4">
      <EclipseGlow />
      <div className="relative w-full max-w-sm rounded-2xl border border-border bg-surface p-8 shadow-raised">
        <Link to="/" className="mb-4 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" data-cursor-hover>
          <ArrowLeft className="h-3.5 w-3.5" /> Back to home
        </Link>
        <BrandLogo className="mb-6" />
        <h1 className="text-xl font-semibold">Login to your lab</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Use the credentials your lab admin created for you.
        </p>

        <button
          type="button"
          onClick={fillDemoCredentials}
          className="mt-4 flex w-full items-start gap-2.5 rounded-lg border border-accent/30 bg-accent/10 p-3 text-left text-xs text-accent-foreground hover:bg-accent/15"
        >
          <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
          <div>
            <p className="font-medium">Just want to look around? Use the demo lab.</p>
            <p className="mt-1 font-num">
              {DEMO_CREDENTIALS.email} / {DEMO_CREDENTIALS.password}
            </p>
          </div>
        </button>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-4 space-y-4">
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
            <PasswordInput
              {...register("password")}
              className="mt-1"
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
