import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ClipboardList,
  Calculator,
  FileCheck2,
  History,
  ShieldCheck,
  FileSpreadsheet,
  ArrowRight,
} from "lucide-react";
import { MarketingNav } from "@/components/layout/MarketingNav";
import { EclipseGlow } from "@/components/effects/EclipseGlow";
import { ParticleField } from "@/components/effects/ParticleField";
import { AsciiRipple } from "@/components/effects/AsciiRipple";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";

const WORKFLOW_STEPS = [
  { title: "Register laboratory & testers", desc: "Set up your lab, add testers, reviewers and approvers with scoped roles." },
  { title: "Register instrument", desc: "Capture manufacturer, model, accuracy class, Max/Min/e and technical specs once." },
  { title: "Run a test session", desc: "The system determines which OIML R-76 tests apply — and which are N/A, with a reason." },
  { title: "Enter observations", desc: "Manual entry or Excel/CSV import, validated line by line before it's accepted." },
  { title: "Auto pass/fail via MPE", desc: "Permissible error is calculated automatically against OIML R-76 thresholds." },
  { title: "Review, sign, archive", desc: "A reviewer approves, a standardized PDF/DOCX report is generated and stored." },
];

const CAPABILITIES = [
  { icon: ClipboardList, title: "Instrument master data", desc: "One record per instrument — manufacturer, model, accuracy class, technical parameters — reused across every future test session." },
  { icon: Calculator, title: "OIML R-76 applicability engine", desc: "Applicable and N/A tests are determined automatically per instrument type, with the reasoning preserved on the record." },
  { icon: FileSpreadsheet, title: "Validated data import", desc: "Bring observations in from Excel or CSV; each row is checked before it touches a test result." },
  { icon: FileCheck2, title: "Standardized report generation", desc: "Every approved session produces a consistent, versioned PDF/DOCX test report — no more per-tester spreadsheet formatting." },
  { icon: History, title: "Full instrument test history", desc: "Search and retrieve any prior report for an instrument, with a complete version history." },
  { icon: ShieldCheck, title: "Role-based access & audit trail", desc: "Lab admins, testers, reviewers and approvers each see exactly what their role requires — every action is logged." },
];

export default function Landing() {
  return (
    <div>
      <MarketingNav />

      {/* HERO */}
      <section className="relative overflow-hidden">
        <EclipseGlow />
        <div className="absolute inset-0 opacity-60">
          <ParticleField density={50} />
        </div>
        <div className="container relative py-24 md:py-32">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="mx-auto max-w-2xl text-center"
          >
            <span className="mb-5 inline-block rounded-full border border-border bg-surface/80 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur">
              Legal Metrology · OIML R-76 · Model Approval
            </span>
            <h1 className="text-4xl font-semibold leading-tight md:text-5xl">
              Test reports for weighing instruments,
              <span className="text-primary"> generated right</span>, every time.
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-base text-muted-foreground md:text-lg">
              Replace manual spreadsheets with a structured OIML R-76 workflow —
              automatic MPE calculations, consistent pass/fail determination, and
              a standardized report your lab can stand behind.
            </p>
            <div className="mt-8 flex items-center justify-center gap-3">
              <Button asChild size="lg" variant="primary">
                <Link to="/login">
                  Login to your lab <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="secondary">
                <Link to="/register">Register your laboratory</Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* PROBLEM -> SOLUTION STRIP with ASCII ripple as the visual anchor */}
      <section className="border-y border-border bg-surface">
        <div className="container grid gap-10 py-16 md:grid-cols-2 md:items-center">
          <div>
            <h2 className="text-2xl font-semibold">
              From scattered spreadsheets to one calculation engine
            </h2>
            <div className="mt-6 space-y-4">
              <div className="rounded-xl border border-border bg-muted/50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Today</p>
                <p className="mt-1 text-sm text-foreground">
                  Manually built spreadsheets, inconsistent formats, error-prone
                  MPE calculations, no shared history across testers.
                </p>
              </div>
              <div className="rounded-xl border border-primary/25 bg-primary/5 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-primary">With NAWI TestSuite</p>
                <p className="mt-1 text-sm text-foreground">
                  One validated pipeline from observation to signed-off report —
                  every instrument, every test session, every result, searchable.
                </p>
              </div>
            </div>
          </div>
          <div className="h-72 overflow-hidden rounded-2xl border border-border bg-background md:h-80">
            <AsciiRipple />
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="workflow" className="container py-20">
        <h2 className="text-center text-2xl font-semibold md:text-3xl">How a test session flows</h2>
        <p className="mx-auto mt-2 max-w-lg text-center text-sm text-muted-foreground">
          The same six stages your team already does by hand — just connected, validated and automatic.
        </p>
        <div className="relative mt-14 grid gap-8 md:grid-cols-3 lg:grid-cols-6">
          <div className="absolute left-0 right-0 top-5 hidden h-px bg-border lg:block" />
          {WORKFLOW_STEPS.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.4, delay: i * 0.06 }}
              className="relative"
            >
              <div className="relative z-10 mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-primary font-num text-sm font-semibold text-primary-foreground">
                {i + 1}
              </div>
              <h3 className="text-sm font-semibold">{step.title}</h3>
              <p className="mt-1 text-xs text-muted-foreground">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CAPABILITIES */}
      <section id="capabilities" className="bg-surface py-20">
        <div className="container">
          <h2 className="text-center text-2xl font-semibold md:text-3xl">Built for what a type-evaluation lab actually needs</h2>
          <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {CAPABILITIES.map((cap, i) => (
              <motion.div
                key={cap.title}
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.4, delay: (i % 3) * 0.08 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <cap.icon className="h-5 w-5" />
                    </div>
                    <CardTitle>{cap.title}</CardTitle>
                    <CardDescription>{cap.desc}</CardDescription>
                  </CardHeader>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* COMPLIANCE STRIP */}
      <section id="compliance" className="container py-16 text-center">
        <p className="text-sm text-muted-foreground">
          Built around <span className="font-medium text-foreground">OIML Recommendation R-76</span> for
          Non-Automatic Weighing Instruments, and aligned with the{" "}
          <span className="font-medium text-foreground">Legal Metrology Act, 2009</span> and the{" "}
          <span className="font-medium text-foreground">Legal Metrology (General) Rules, 2011</span> —
          developed for Smart India Hackathon 2026, Ministry of Consumer Affairs, Food &amp; Public Distribution
          (Department of Consumer Affairs).
        </p>
      </section>

      <footer className="border-t border-border py-8">
        <div className="container flex flex-col items-center justify-between gap-3 text-xs text-muted-foreground md:flex-row">
          <span>© {new Date().getFullYear()} NAWI TestSuite</span>
          <span>Smart India Hackathon · Problem Statement 26035</span>
        </div>
      </footer>
    </div>
  );
}
