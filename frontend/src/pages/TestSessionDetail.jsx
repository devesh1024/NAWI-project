import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { ArrowLeft, Plus, FileDown, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useAuth } from "@/hooks/useAuth";
import { api, downloadResponse } from "@/lib/apiClient";

const STATUS_FLOW = ["DRAFT", "IN PROGRESS", "SUBMITTED", "UNDER REVIEW", "APPROVED", "REJECTED"];
// Only these roles can approve, per the backend's require_lab_admin /
// reviewer check on PATCH .../approve-report — TODO: confirm exact role
// set with backend if this changes.
const APPROVER_ROLES = ["LAB_ADMIN", "REVIEWER"];

function resultBadge(pass_fail) {
  if (pass_fail === "PASS") return "pass";
  if (pass_fail === "FAIL") return "fail";
  return "pending";
}

export default function TestSessionDetail() {
  const { id } = useParams();
  const { token, role } = useAuth();

  const [session, setSession] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [testDefinitions, setTestDefinitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    setLoadError("");
    try {
      const [s, rd, td] = await Promise.all([
        api.getTestSession(id, token),
        // report-data works even before a report is generated — it's the
        // only read endpoint that returns a session's tests/observations/
        // calculations/results, so it doubles as the "current progress" view.
        api.getReportData(id, token).catch(() => null),
        api.getTestDefinitions(token),
      ]);
      setSession(s);
      setReportData(rd);
      setTestDefinitions(td.filter((t) => t.standard_id === s.standard_id && t.active));
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) load();
  }, [token, id]);

  async function handleStatusChange(newStatus) {
    setActionError("");
    setBusy(true);
    try {
      await api.updateTestSessionStatus(id, newStatus, token);
      await load();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleGenerateReport() {
    setActionError("");
    setBusy(true);
    try {
      const res = await api.generateReport(id, token);
      await downloadResponse(res, `NAWI_Report_${id}.docx`);
      await load();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDownload(type) {
    setActionError("");
    try {
      const res = type === "pdf" ? await api.downloadPdf(id, token) : await api.downloadDocx(id, token);
      await downloadResponse(res, `NAWI_Report_${id}.${type}`);
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function handleApprove() {
    setActionError("");
    setBusy(true);
    try {
      await api.approveReport(id, token);
      await load();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <p className="py-12 text-center text-sm text-muted-foreground">Loading session…</p>;
  if (loadError) return <p className="py-12 text-center text-sm text-status-fail">{loadError}</p>;
  if (!session) return null;

  const canApprove = APPROVER_ROLES.includes(role);

  return (
    <div className="space-y-6">
      <Link to="/app/test-sessions" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" data-cursor-hover>
        <ArrowLeft className="h-3.5 w-3.5" /> Back to test sessions
      </Link>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold font-num">{session.session_number || session.test_session_id.slice(0, 8)}</h1>
          <p className="text-sm text-muted-foreground">{session.application_number || "No application number"}</p>
        </div>
        <div className="flex items-center gap-2">
          {session.overall_result && <StatusBadge status={resultBadge(session.overall_result)} animate />}
          <select
            value={session.status}
            onChange={(e) => handleStatusChange(e.target.value)}
            disabled={busy}
            className="rounded-lg border border-input bg-surface px-3 py-1.5 text-xs font-medium outline-none focus:ring-2 focus:ring-ring"
          >
            {STATUS_FLOW.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {actionError && <p className="rounded-lg bg-status-fail/10 px-3 py-2 text-xs text-status-fail">{actionError}</p>}

      <EnvironmentalConditions sessionId={id} token={token} />

      <AddTestPanel sessionId={id} token={token} testDefinitions={testDefinitions} onAdded={load} />

      <div className="space-y-4">
        {(reportData?.tests || []).map((t) => (
          <SessionTestCard key={t.session_test_id} test={t} token={token} onChanged={load} />
        ))}
        {(!reportData?.tests || reportData.tests.length === 0) && (
          <p className="rounded-lg border border-dashed border-border py-8 text-center text-sm text-muted-foreground">
            No tests added yet — add one above.
          </p>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Report</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2 pt-0">
          <Button onClick={handleGenerateReport} disabled={busy}>
            <FileDown className="h-4 w-4" /> Generate report (DOCX)
          </Button>
          <Button variant="secondary" onClick={() => handleDownload("pdf")}>
            <FileDown className="h-4 w-4" /> Download PDF
          </Button>
          <Button variant="secondary" onClick={() => handleDownload("docx")}>
            <FileDown className="h-4 w-4" /> Download DOCX
          </Button>
          {canApprove && (
            <Button variant="accent" onClick={handleApprove} disabled={busy}>
              <CheckCircle2 className="h-4 w-4" /> Approve report
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------

function EnvironmentalConditions({ sessionId, token }) {
  const [saved, setSaved] = useState(false);
  const { register, handleSubmit, formState: { isSubmitting } } = useForm();

  async function onSubmit(values) {
    const payload = {
      test_session_id: sessionId,
      ...Object.fromEntries(
        Object.entries(values)
          .filter(([, v]) => v !== "")
          .map(([k, v]) => [k, k === "source" ? v : Number(v)])
      ),
    };
    await api.addEnvironmentalCondition(payload, token);
    setSaved(true);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Environmental conditions</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-3 sm:grid-cols-4">
          <input type="number" step="any" placeholder="Temperature (°C)" {...register("temperature")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <input type="number" step="any" placeholder="Humidity (%)" {...register("humidity")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <input type="number" step="any" placeholder="Pressure (hPa)" {...register("pressure")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <Button type="submit" size="sm" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Record"}</Button>
        </form>
        {saved && <p className="mt-2 text-xs text-status-pass">Recorded.</p>}
      </CardContent>
    </Card>
  );
}

function AddTestPanel({ sessionId, token, testDefinitions, onAdded }) {
  const [error, setError] = useState("");
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm({
    defaultValues: { applicability_status: "APPLICABLE" },
  });

  async function onSubmit(values) {
    setError("");
    try {
      await api.addTestToSession(sessionId, values, token);
      reset({ applicability_status: "APPLICABLE" });
      onAdded();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add a test</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-3 sm:grid-cols-[1fr_auto_auto]">
          <select {...register("test_definition_id", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm">
            <option value="">Select test from this standard…</option>
            {testDefinitions.map((t) => (
              <option key={t.test_definition_id} value={t.test_definition_id}>{t.test_code} — {t.test_name}</option>
            ))}
          </select>
          <select {...register("applicability_status")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm">
            <option value="APPLICABLE">Applicable</option>
            <option value="NOT_APPLICABLE">N/A</option>
          </select>
          <Button type="submit" disabled={isSubmitting}><Plus className="h-4 w-4" /> Add</Button>
        </form>
        <input placeholder="N/A reason (if not applicable)" {...register("na_reason")} className="mt-2 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" />
        {error && <p className="mt-2 text-xs text-status-fail">{error}</p>}
      </CardContent>
    </Card>
  );
}

function SessionTestCard({ test, token, onChanged }) {
  const [obsError, setObsError] = useState("");
  const [calcError, setCalcError] = useState("");
  const obsForm = useForm();
  const calcForm = useForm();
  const hasResult = test.results && test.results.length > 0;
  const latestResult = hasResult ? test.results[test.results.length - 1] : null;

  async function onAddObservation(values) {
    setObsError("");
    try {
      const payload = {
        ...values,
        value_numeric: values.value_numeric === "" ? undefined : Number(values.value_numeric),
      };
      await api.addObservation(test.session_test_id, payload, token);
      obsForm.reset();
      onChanged();
    } catch (err) {
      setObsError(err.message);
    }
  }

  // Manual entry until the OIML calculation engine (MPE lookup + pass/fail)
  // is wired in server-side — this form just records whatever the tester
  // enters, matching what POST .../calculation-result currently accepts.
  async function onSaveCalculation(values) {
    setCalcError("");
    try {
      const payload = Object.fromEntries(
        Object.entries(values)
          .filter(([, v]) => v !== "")
          .map(([k, v]) => [k, ["measured_value", "mpe_value", "error_value", "corrected_error"].includes(k) ? Number(v) : v])
      );
      await api.saveCalculationResult(test.session_test_id, payload, token);
      calcForm.reset();
      onChanged();
    } catch (err) {
      setCalcError(err.message);
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{test.test_code} — {test.test_name}</CardTitle>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {test.applicability_status === "NOT_APPLICABLE" ? `N/A — ${test.na_reason || "no reason given"}` : test.category || ""}
              </p>
            </div>
            {test.result && <StatusBadge status={resultBadge(test.result)} />}
          </div>
        </CardHeader>
        <CardContent className="space-y-4 pt-0">
          {test.applicability_status !== "NOT_APPLICABLE" && (
            <>
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Observations</p>
                {test.observations?.length > 0 && (
                  <table className="mb-2 w-full text-xs">
                    <tbody>
                      {test.observations.map((o) => (
                        <tr key={o.observation_id} className="border-t border-border">
                          <td className="py-1.5">{o.parameter_name}</td>
                          <td className="py-1.5 font-num">{o.value_numeric ?? o.value_text ?? "—"} {o.unit || ""}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                <form onSubmit={obsForm.handleSubmit(onAddObservation)} className="grid gap-2 sm:grid-cols-[1fr_auto_auto_auto]">
                  <input placeholder="Parameter (e.g. Indicated value)" {...obsForm.register("parameter_name", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-xs" />
                  <input type="number" step="any" placeholder="Value" {...obsForm.register("value_numeric")} className="w-24 rounded-lg border border-input bg-background px-3 py-2 text-xs" />
                  <input placeholder="Unit" {...obsForm.register("unit")} className="w-20 rounded-lg border border-input bg-background px-3 py-2 text-xs" />
                  <Button type="submit" size="sm"><Plus className="h-3.5 w-3.5" /></Button>
                </form>
                {obsError && <p className="mt-1 text-xs text-status-fail">{obsError}</p>}
              </div>

              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Calculation result {latestResult && "(recorded)"}
                </p>
                {latestResult ? (
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 rounded-lg bg-muted/50 p-3 text-xs sm:grid-cols-4">
                    <span>Measured: <span className="font-num">{latestResult.measured_value ?? "—"}</span></span>
                    <span>MPE: <span className="font-num">{latestResult.mpe_value ?? "—"}</span></span>
                    <span>Error: <span className="font-num">{latestResult.error_value ?? "—"}</span></span>
                    <span>Result: <span className="font-num">{latestResult.pass_fail ?? "—"}</span></span>
                  </div>
                ) : (
                  <form onSubmit={calcForm.handleSubmit(onSaveCalculation)} className="grid gap-2 sm:grid-cols-3">
                    <input type="number" step="any" placeholder="Measured value" {...calcForm.register("measured_value")} className="rounded-lg border border-input bg-background px-3 py-2 text-xs" />
                    <input type="number" step="any" placeholder="MPE value" {...calcForm.register("mpe_value")} className="rounded-lg border border-input bg-background px-3 py-2 text-xs" />
                    <input type="number" step="any" placeholder="Error value" {...calcForm.register("error_value")} className="rounded-lg border border-input bg-background px-3 py-2 text-xs" />
                    <select {...calcForm.register("pass_fail", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-xs">
                      <option value="">Pass/Fail…</option>
                      <option value="PASS">PASS</option>
                      <option value="FAIL">FAIL</option>
                    </select>
                    <input placeholder="Result summary (optional)" {...calcForm.register("result_summary")} className="rounded-lg border border-input bg-background px-3 py-2 text-xs sm:col-span-1" />
                    <Button type="submit" size="sm" disabled={calcForm.formState.isSubmitting}>Save result</Button>
                  </form>
                )}
                {calcError && <p className="mt-1 text-xs text-status-fail">{calcError}</p>}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
