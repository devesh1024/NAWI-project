import React, { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { ArrowLeft, Plus, FileDown, Check, ShieldAlert, Info, Undo2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SessionStatus } from "@/components/ui/SessionStatus";
import { useAuth } from "@/hooks/useAuth";
import { api, downloadResponse } from "@/lib/apiClient";
import { STATUS_HELP, roleTone } from "@/lib/roles";
import { cn } from "@/lib/utils";
import { TEST_INPUT_TEMPLATES, DEDICATED_FORM_TEST_CODES } from "@/lib/calculationTemplates";

const STEPS = [
  { key: "DRAFT", label: "Draft" },
  { key: "IN PROGRESS", label: "Testing" },
  { key: "SUBMITTED", label: "Submitted" },
  { key: "UNDER REVIEW", label: "Review" },
  { key: "APPROVED", label: "Approved" },
];

// What this person does on a session, in one sentence.
const ROLE_ON_SESSION = {
  LAB_ADMIN: "You sign off final reports. You do not test, so you can review and approve any session you did not test.",
  TECHNICAL_MANAGER: "You oversee the technical work and can review or sign sessions you did not test.",
  QUALITY_MANAGER: "You have read-only access here. Quality stays independent of testing.",
  REVIEWER: "You check the tester's work and report, then return it or forward it for signature.",
  APPROVER: "You sign reports a reviewer has forwarded to you: approve or reject.",
  TESTER: "You plan the tests, run the calculations and submit the work for review.",
  ASSISTANT: "You record readings and conditions. The tester calculates and submits.",
  RECORDS_OFFICER: "You keep instrument records. Sessions are read-only for you.",
  STANDARDS_CUSTODIAN: "You keep the reference standards. Sessions are read-only for you.",
  AUDITOR: "Read-only access, for assessment.",
};

function resultBadge(pass_fail) {
  if (pass_fail === "PASS") return "pass";
  if (pass_fail === "FAIL") return "fail";
  if (pass_fail === "N/A") return "na";
  return "pending";
}

function when(iso) {
  return iso ? new Date(iso).toLocaleString([], { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
}

const HISTORY_TEXT = {
  START_WORK: "started testing",
  SUBMIT: "submitted the session for review",
  RECALL: "recalled the session to edit it",
  START_REVIEW: "started the review",
  RETURN_FOR_CORRECTION: "returned it for correction",
  REWORK: "reopened it to rework",
  SUBMIT_FOR_APPROVAL: "forwarded the report for approval",
  APPROVE: "approved and signed the report",
  REJECT: "rejected the report",
  GENERATE_REPORT: "generated the report",
  CREATE: "created the session",
  UPDATE: "updated the session",
};

export default function TestSessionDetail() {
  const { id } = useParams();
  const { token, role, roleLabel } = useAuth();

  const [session, setSession] = useState(null);
  const [instrument, setInstrument] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  // `tests` is seeded from report-data on load, then mutated locally as
  // tests/observations/calculations are added: only this array updates, via
  // the exact object the API just returned, no refetch.
  const [tests, setTests] = useState([]);
  const [testDefinitions, setTestDefinitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState(false);
  const [asking, setAsking] = useState(null); // an action waiting for its reason

  const load = useCallback(async () => {
    setLoadError("");
    try {
      const [s, rd, td, wf] = await Promise.all([
        api.getTestSession(id, token),
        api.getReportData(id, token).catch(() => null),
        api.getTestDefinitions(token),
        api.getSessionWorkflow(id, token),
      ]);
      setSession(s);
      setWorkflow(wf);
      setTests(rd?.tests || []);
      setTestDefinitions(td.filter((t) => t.standard_id === s.standard_id && t.active));
      api.getInstrument(s.instrument_id, token).then(setInstrument).catch(() => setInstrument(null));
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }, [id, token]);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  // Light refresh after something changes: who can do what next.
  const refreshWorkflow = useCallback(async () => {
    try {
      setWorkflow(await api.getSessionWorkflow(id, token));
    } catch { /* keep what we have */ }
  }, [id, token]);

  function handleTestAdded(newSessionTest) {
    const def = testDefinitions.find((t) => t.test_definition_id === newSessionTest.test_definition_id);
    setTests((prev) => [
      ...prev,
      { ...newSessionTest, test_code: def?.test_code, test_name: def?.test_name, category: def?.category, observations: [], results: [] },
    ]);
    refreshWorkflow();
  }

  function handleObservationAdded(sessionTestId, observation) {
    setTests((prev) =>
      prev.map((t) =>
        t.session_test_id === sessionTestId ? { ...t, observations: [...(t.observations || []), observation] } : t
      )
    );
  }

  function handleCalculationSaved(sessionTestId, result) {
    setTests((prev) =>
      prev.map((t) =>
        t.session_test_id === sessionTestId
          ? { ...t, result: result.pass_fail, results: [...(t.results || []), result] }
          : t
      )
    );
  }

  // One handler for every workflow button: the backend decides what each does.
  async function runAction(action, reason) {
    setActionError("");
    setBusy(true);
    try {
      if (action.key === "forward_for_approval") await api.submitReportForApproval(id, token);
      else if (action.key === "approve") await api.approveReport(id, token, "APPROVE");
      else if (action.key === "reject") await api.approveReport(id, token, "REJECT", reason);
      else await api.updateTestSessionStatus(id, action.to, token, reason);
      setAsking(null);
      await load();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function onAction(action) {
    if (action.needs_reason) setAsking({ action, text: "" });
    else runAction(action);
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

  if (loading) return <p className="py-12 text-center text-sm text-muted-foreground">Loading session…</p>;
  if (loadError) return <p className="py-12 text-center text-sm text-status-fail">{loadError}</p>;
  if (!session || !workflow) return null;

  const canEnter = workflow.can_enter_data;
  const canCalculate = workflow.can_plan_and_calculate;
  const instrumentName = instrument
    ? [instrument.manufacturer, instrument.model].filter(Boolean).join(" ") || instrument.instrument_code
    : null;

  // The latest correction note, shown to whoever has to act on it.
  const returnNote = [...(workflow.history || [])]
    .reverse()
    .find((h) => ["RETURN_FOR_CORRECTION", "REJECT"].includes(h.action) && h.remarks);

  return (
    <div className="space-y-6">
      <Link to="/app/test-sessions" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" data-cursor-hover>
        <ArrowLeft className="h-3.5 w-3.5" /> Back to test sessions
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="font-num text-2xl font-semibold">{session.session_number || session.test_session_id.slice(0, 8)}</h1>
            <SessionStatus status={session.status} />
            {session.overall_result && <StatusBadge status={resultBadge(session.overall_result)} animate />}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {[instrumentName, session.application_number || "No application number"].filter(Boolean).join(" · ")}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Tester: <span className="font-medium text-foreground">{session.tester_name || "—"}</span>
            {session.reviewer_name && (
              <> · Reviewer: <span className="font-medium text-foreground">{session.reviewer_name}</span></>
            )}
          </p>
        </div>
      </div>

      <Stepper status={session.status} />

      {session.status === "REJECTED" && returnNote && (
        <div className="flex gap-3 rounded-xl border border-status-fail/30 bg-status-fail/5 p-4" role="alert">
          <Undo2 className="mt-0.5 h-4 w-4 shrink-0 text-status-fail" />
          <div className="text-sm">
            <p className="font-medium text-status-fail">Returned for correction</p>
            <p className="mt-0.5">{returnNote.remarks}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {returnNote.by}{returnNote.by_role ? ` (${returnNote.by_role})` : ""} · {when(returnNote.at)}
            </p>
          </div>
        </div>
      )}

      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>What happens next</CardTitle>
            <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium", roleTone(role))}>{roleLabel}</span>
          </div>
          <p className="text-xs text-muted-foreground">{STATUS_HELP[session.status]}</p>
        </CardHeader>
        <CardContent className="space-y-3 pt-0">
          <p className="flex gap-2 text-xs text-muted-foreground">
            <Info className="mt-px h-3.5 w-3.5 shrink-0" />
            {ROLE_ON_SESSION[role] || ""}
          </p>

          {workflow.took_part && ["REVIEWER", "APPROVER", "LAB_ADMIN", "TECHNICAL_MANAGER"].includes(role) && (
            <p className="flex gap-2 rounded-lg bg-status-pending/10 px-3 py-2 text-xs text-status-pending" role="note">
              <ShieldAlert className="mt-px h-3.5 w-3.5 shrink-0" />
              You took part in testing this session, so someone else has to review and sign it. This keeps the checker independent of the maker.
            </p>
          )}

          {workflow.actions.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {workflow.actions.map((a) => (
                <div key={a.key} className="flex flex-col">
                  <Button
                    onClick={() => onAction(a)}
                    disabled={busy || !a.enabled}
                    variant={a.key === "approve" ? "accent" : a.key === "reject" || a.key === "return_for_correction" ? "destructive" : a.enabled ? "primary" : "secondary"}
                    size="sm"
                    title={a.reason || undefined}
                  >
                    <Check className="h-4 w-4" /> {a.label}
                  </Button>
                  {!a.enabled && a.reason && (
                    <span className="mt-1 max-w-xs text-[11px] leading-snug text-muted-foreground">{a.reason}</span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              {nothingToDo(role, session.status, workflow)}
            </p>
          )}

          {asking && (
            <form
              onSubmit={(e) => { e.preventDefault(); runAction(asking.action, asking.text.trim()); }}
              className="space-y-2 rounded-lg border border-border bg-muted/40 p-3"
            >
              <label className="text-sm font-medium" htmlFor="reason">
                {asking.action.key === "reject" ? "Why is the report being rejected?" : "What needs to be corrected?"}
              </label>
              <textarea
                id="reason"
                autoFocus
                rows={3}
                value={asking.text}
                onChange={(e) => setAsking({ ...asking, text: e.target.value })}
                placeholder="Be specific: the tester will see this."
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
              <div className="flex gap-2">
                <Button type="submit" size="sm" variant="destructive" disabled={busy || !asking.text.trim()}>
                  {asking.action.label}
                </Button>
                <Button type="button" size="sm" variant="secondary" onClick={() => setAsking(null)}>Cancel</Button>
              </div>
            </form>
          )}

          {actionError && <p className="rounded-lg bg-status-fail/10 px-3 py-2 text-xs text-status-fail">{actionError}</p>}
        </CardContent>
      </Card>

      <EnvironmentalConditions sessionId={id} token={token} canEdit={canEnter} />

      {canCalculate && (
        <AddTestPanel sessionId={id} token={token} testDefinitions={testDefinitions} onAdded={handleTestAdded} />
      )}

      <div className="space-y-4">
        {tests.map((t) => (
          <SessionTestCard
            key={t.session_test_id}
            test={t}
            token={token}
            canEnter={canEnter}
            canCalculate={canCalculate}
            onObservationAdded={handleObservationAdded}
            onCalculationSaved={handleCalculationSaved}
          />
        ))}
        {tests.length === 0 && (
          <p className="rounded-lg border border-dashed border-border py-8 text-center text-sm text-muted-foreground">
            {canCalculate ? "No tests added yet. Add one above." : "The tester has not added any tests yet."}
          </p>
        )}
      </div>

      {(workflow.can_generate_report || workflow.report_available) && (
        <Card>
          <CardHeader><CardTitle>Report</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap gap-2 pt-0">
            {workflow.can_generate_report && (
              <Button onClick={handleGenerateReport} disabled={busy}>
                <FileDown className="h-4 w-4" /> {workflow.report_available ? "Regenerate report (DOCX)" : "Generate report (DOCX)"}
              </Button>
            )}
            {workflow.report_available && (
              <>
                <Button variant="secondary" onClick={() => handleDownload("pdf")}>
                  <FileDown className="h-4 w-4" /> Download PDF
                </Button>
                <Button variant="secondary" onClick={() => handleDownload("docx")}>
                  <FileDown className="h-4 w-4" /> Download DOCX
                </Button>
              </>
            )}
            {workflow.report_status && (
              <span className="ml-auto self-center text-xs text-muted-foreground">
                Report status: <span className="font-medium text-foreground">{workflow.report_status.replace(/_/g, " ").toLowerCase()}</span>
              </span>
            )}
          </CardContent>
        </Card>
      )}

      <History items={workflow.history} />
    </div>
  );
}

function nothingToDo(role, status, workflow) {
  if (["AUDITOR", "QUALITY_MANAGER", "RECORDS_OFFICER", "STANDARDS_CUSTODIAN"].includes(role)) {
    return "You can read this session but not change it.";
  }
  if (status === "APPROVED") return "This session is approved. It is final and locked.";
  if (role === "ASSISTANT") return workflow.can_enter_data ? "Record readings and conditions below." : "This session has moved on from data entry.";
  if (role === "TESTER") {
    if (status === "SUBMITTED" || status === "UNDER REVIEW") return "Waiting for the reviewers. You will be notified if it is returned.";
    return "Nothing for you to do right now.";
  }
  if (role === "REVIEWER") return status === "SUBMITTED" ? "" : "Nothing for you to do on this session right now.";
  if (role === "APPROVER") return "Nothing for you to sign yet. It arrives here once a reviewer forwards it.";
  return "Nothing for you to do on this session right now.";
}

function Stepper({ status }) {
  const returned = status === "REJECTED";
  const current = returned ? 1 : Math.max(0, STEPS.findIndex((s) => s.key === status));

  return (
    <ol className="flex items-center gap-1 overflow-x-auto rounded-xl border border-border bg-surface px-4 py-3" aria-label="Session progress">
      {STEPS.map((step, i) => {
        const done = i < current || status === "APPROVED";
        const active = i === current && status !== "APPROVED";
        return (
          <React.Fragment key={step.key}>
            <li className="flex shrink-0 items-center gap-2" aria-current={active ? "step" : undefined}>
              <span
                className={cn(
                  "font-num flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-semibold",
                  done && "bg-status-pass text-white",
                  active && !returned && "bg-primary text-primary-foreground",
                  active && returned && "bg-status-fail text-white",
                  !done && !active && "bg-muted text-muted-foreground"
                )}
              >
                {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
              </span>
              <span className={cn("text-xs", active || done ? "font-medium text-foreground" : "text-muted-foreground")}>
                {active && returned ? "Returned" : step.label}
              </span>
            </li>
            {i < STEPS.length - 1 && <span className={cn("mx-1 h-px min-w-4 flex-1", i < current ? "bg-status-pass" : "bg-border")} />}
          </React.Fragment>
        );
      })}
    </ol>
  );
}

function History({ items }) {
  if (!items?.length) return null;
  return (
    <Card>
      <CardHeader><CardTitle>History</CardTitle></CardHeader>
      <CardContent className="pt-0">
        <ol className="space-y-3 border-l border-border pl-4">
          {items.map((h, i) => (
            <li key={i} className="relative text-sm">
              <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-primary" aria-hidden="true" />
              <p>
                <span className="font-medium">{h.by || "System"}</span>
                {h.by_role && <span className="text-muted-foreground"> ({h.by_role})</span>}{" "}
                {HISTORY_TEXT[h.action] || h.action.toLowerCase().replace(/_/g, " ")}
              </p>
              {h.remarks && <p className="mt-0.5 text-xs text-muted-foreground">“{h.remarks}”</p>}
              <p className="font-num text-[11px] text-muted-foreground">{when(h.at)}</p>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------

function EnvironmentalConditions({ sessionId, token, canEdit }) {
  const [records, setRecords] = useState([]);
  const [error, setError] = useState("");
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm();

  useEffect(() => {
    api.getEnvironmentalConditions(sessionId, token).then(setRecords).catch(() => setRecords([]));
  }, [sessionId, token]);

  async function onSubmit(values) {
    setError("");
    const payload = {
      test_session_id: sessionId,
      ...Object.fromEntries(
        Object.entries(values)
          .filter(([, v]) => v !== "")
          .map(([k, v]) => [k, k === "source" ? v : Number(v)])
      ),
    };
    try {
      const created = await api.addEnvironmentalCondition(payload, token);
      setRecords((prev) => [...prev, created]);
      reset();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Environmental conditions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        {canEdit && (
          <form onSubmit={handleSubmit(onSubmit)} className="grid gap-3 sm:grid-cols-4">
            <input type="number" step="any" placeholder="Temperature (°C)" {...register("temperature")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
            <input type="number" step="any" placeholder="Humidity (%)" {...register("humidity")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
            <input type="number" step="any" placeholder="Pressure (hPa)" {...register("pressure")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
            <Button type="submit" size="sm" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Record"}</Button>
          </form>
        )}
        {error && <p className="text-xs text-status-fail">{error}</p>}
        {records.length > 0 ? (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="pb-1 font-medium">Recorded</th>
                <th className="pb-1 font-medium">Temperature</th>
                <th className="pb-1 font-medium">Humidity</th>
                <th className="pb-1 font-medium">Pressure</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.environment_id} className="border-t border-border">
                  <td className="font-num py-1.5">{when(r.recorded_at)}</td>
                  <td className="font-num py-1.5">{r.temperature ?? "—"} {r.temperature != null ? "°C" : ""}</td>
                  <td className="font-num py-1.5">{r.humidity ?? "—"} {r.humidity != null ? "%" : ""}</td>
                  <td className="font-num py-1.5">{r.pressure ?? "—"} {r.pressure != null ? "hPa" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          !canEdit && <p className="text-xs text-muted-foreground">No conditions were recorded.</p>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Submits { inputs: {...} } to POST .../calculation-result — the backend's
 * R76 engine computes measured_value/mpe_value/error_value/pass_fail
 * itself now (see backend/app/services/calculation_engine/). WP, ZR,
 * TEMP_STATIC, TEMP_NO_LOAD, ECC_WEIGHT and REP get dedicated forms; every
 * other test code falls back to a JSON textarea pre-filled with an accurate
 * template (see src/lib/calculationTemplates.js) since each has a very
 * specific, OIML-prescribed structure/cardinality.
 *
 * KNOWN ISSUE (backend, not fixable from here): the engine strictly requires
 * Python Decimal instances and the API currently passes raw JSON numbers
 * straight through — so submitting any of these will likely 422 with
 * something like "indicated_value must be a Decimal" until the backend adds
 * a JSON→Decimal conversion step in calculation_routes.py before calling
 * engine.calculate(). This form is correct and ready for when that lands.
 */
function CalculationForm({ sessionTestId, testCode, token, onSaved }) {
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const isDedicated = DEDICATED_FORM_TEST_CODES.includes(testCode);

  async function submitInputs(inputs) {
    setError("");
    setSubmitting(true);
    try {
      const response = await api.saveCalculationResult(sessionTestId, { inputs }, token);
      // response.result already matches the TestResult row shape
      // (measured_value/mpe_value/error_value/pass_fail/result_summary) —
      // pass it straight up so the parent can merge it into local state
      // without a refetch.
      onSaved(response.result);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (testCode === "WP") return <WeighingPerformanceForm onSubmit={submitInputs} submitting={submitting} error={error} />;
  if (testCode === "ZR") return <ZeroReturnForm onSubmit={submitInputs} submitting={submitting} error={error} />;
  if (testCode === "TEMP_STATIC") return <StaticTemperatureForm onSubmit={submitInputs} submitting={submitting} error={error} />;
  if (testCode === "TEMP_NO_LOAD") return <TempNoLoadForm onSubmit={submitInputs} submitting={submitting} error={error} />;
  if (testCode === "ECC_WEIGHT") return <EccentricityForm onSubmit={submitInputs} submitting={submitting} error={error} />;
  if (testCode === "REP") return <RepeatabilityForm onSubmit={submitInputs} submitting={submitting} error={error} />;
  if (testCode === "DIS") { return (<DiscriminationForm onSubmit={submitInputs} submitting={submitting} error={error} />); }
  if (testCode === "SPAN") {
    return (
      <SpanStabilityForm
        onSubmit={submitInputs}
        submitting={submitting}
        error={error}
      />
    );
  }
  if (testCode === "VOLT") {
    return (
      <VoltageVariationForm
        onSubmit={submitInputs}
        submitting={submitting}
        error={error}
      />
    );
  }
  if (testCode === "WARMUP") {
    return (
      <WarmupForm
        onSubmit={submitInputs}
        submitting={submitting}
        error={error}
      />
    );
  }
  if (testCode === "TARE") {
    return (
      <TareForm
        onSubmit={submitInputs}
        submitting={submitting}
        error={error}
      />
    );
  }

  if (testCode === "CRP") {
    return (
      <CreepForm
        onSubmit={submitInputs}
        submitting={submitting}
        error={error}
      />
    );
  }
  return <GenericJsonForm testCode={testCode} onSubmit={submitInputs} submitting={submitting} error={error} />;
}

function WeighingPerformanceForm({ onSubmit, submitting, error }) {
  const [rows, setRows] = useState([{ load: "", indication: "", additional_load: "0", zero_error: "0" }]);

  function updateRow(i, key, value) {
    setRows((r) => r.map((row, idx) => (idx === i ? { ...row, [key]: value } : row)));
  }

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({
      measurements: rows.map((r) => ({
        load: Number(r.load),
        indication: Number(r.indication),
        additional_load: Number(r.additional_load || 0),
        zero_error: Number(r.zero_error || 0),
      })),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      {rows.map((row, i) => (
        <div key={i} className="grid grid-cols-5 gap-2">
          <input type="number" step="any" placeholder="Load" value={row.load} onChange={(e) => updateRow(i, "load", e.target.value)} required className="rounded-lg border border-input bg-background px-3 py-2 text-xs" />
          <input type="number" step="any" placeholder="Indication" value={row.indication} onChange={(e) => updateRow(i, "indication", e.target.value)} required className="rounded-lg border border-input bg-background px-3 py-2 text-xs" />
          <input type="number" step="any" placeholder="Additional load" value={row.additional_load} onChange={(e) => updateRow(i, "additional_load", e.target.value)} className="rounded-lg border border-input bg-background px-3 py-2 text-xs" />
          <input type="number" step="any" placeholder="Zero error" value={row.zero_error} onChange={(e) => updateRow(i, "zero_error", e.target.value)} className="rounded-lg border border-input bg-background px-3 py-2 text-xs" />
          {rows.length > 1 && (
            <button type="button" onClick={() => setRows((r) => r.filter((_, idx) => idx !== i))} className="text-xs text-status-fail">Remove</button>
          )}
        </div>
      ))}
      <div className="flex items-center gap-2">
        <Button type="button" size="sm" variant="secondary" onClick={() => setRows((r) => [...r, { load: "", indication: "", additional_load: "0", zero_error: "0" }])}>
          <Plus className="h-3.5 w-3.5" /> Add measurement
        </Button>
        <Button type="submit" size="sm" disabled={submitting}>{submitting ? "Calculating…" : "Run calculation"}</Button>
      </div>
      {error && <p className="text-xs text-status-fail">{error}</p>}
    </form>
  );
}

function ZeroReturnForm({ onSubmit, submitting, error }) {
  const [values, setValues] = useState({ load: "", zero_before: "", zero_after: "", automatic_zero_tracking_disabled: true });

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({
      load: Number(values.load),
      zero_before: Number(values.zero_before),
      zero_after: Number(values.zero_after),
      automatic_zero_tracking_disabled: values.automatic_zero_tracking_disabled,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-2 sm:grid-cols-4">
      <input type="number" step="any" placeholder="Load" value={values.load} onChange={(e) => setValues((v) => ({ ...v, load: e.target.value }))} required className="rounded-lg border border-input bg-background px-3 py-2 text-xs" />
      <input type="number" step="any" placeholder="Zero before" value={values.zero_before} onChange={(e) => setValues((v) => ({ ...v, zero_before: e.target.value }))} required className="rounded-lg border border-input bg-background px-3 py-2 text-xs" />
      <input type="number" step="any" placeholder="Zero after" value={values.zero_after} onChange={(e) => setValues((v) => ({ ...v, zero_after: e.target.value }))} required className="rounded-lg border border-input bg-background px-3 py-2 text-xs" />
      <Button type="submit" size="sm" disabled={submitting}>{submitting ? "Calculating…" : "Run calculation"}</Button>
      <label className="col-span-full flex items-center gap-2 text-xs text-muted-foreground">
        <input type="checkbox" checked={values.automatic_zero_tracking_disabled} onChange={(e) => setValues((v) => ({ ...v, automatic_zero_tracking_disabled: e.target.checked }))} />
        Automatic zero-tracking disabled during this test (required by §3.9.4.2)
      </label>
      {error && <p className="col-span-full text-xs text-status-fail">{error}</p>}
    </form>
  );
}

function StaticTemperatureForm({ onSubmit, submitting, error }) {
  const TEMPERATURES = [20, 40, -10, 5, 20];
  const [rows, setRows] = useState(
    TEMPERATURES.map((temperature) => ({
      temperature,
      loading_indication: "",
      loading_additional_load: "0",
      loading_zero_error: "0",
      unloading_indication: "",
      unloading_additional_load: "0",
      unloading_zero_error: "0",
    }))
  );
  function updateRow(index, key, value) {
    setRows((current) =>
      current.map((row, i) =>
        i === index ? { ...row, [key]: value } : row
      )
    );
  }
  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({
      load: 10,
      observations: rows.map((row) => ({
        temperature: Number(row.temperature),
        loading: {
          indicated_value: Number(row.loading_indication),
          additional_load: Number(row.loading_additional_load || 0),
          zero_error: Number(row.loading_zero_error || 0),
        },
        unloading: {
          indicated_value: Number(row.unloading_indication),
          additional_load: Number(row.unloading_additional_load || 0),
          zero_error: Number(row.unloading_zero_error || 0),
        },
      })),
    });
  }
  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="overflow-x-auto rounded-lg border border-input">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b bg-muted/30">
              <th className="px-3 py-2 text-left">Temperature (°C)</th>
              <th className="px-3 py-2 text-left">Loading Indication (kg)</th>
              <th className="px-3 py-2 text-left">Loading ΔL (kg)</th>
              <th className="px-3 py-2 text-left">Loading Zero Error (kg)</th>
              <th className="px-3 py-2 text-left">Unloading Indication (kg)</th>
              <th className="px-3 py-2 text-left">Unloading ΔL (kg)</th>
              <th className="px-3 py-2 text-left">Unloading Zero Error (kg)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b last:border-0">
                <td className="px-3 py-2 font-medium">
                  {row.temperature}
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.loading_indication}
                    onChange={(e) =>
                      updateRow(i, "loading_indication", e.target.value)
                    }
                    required
                    className="w-28 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.loading_additional_load}
                    onChange={(e) =>
                      updateRow(i, "loading_additional_load", e.target.value)
                    }
                    className="w-24 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.loading_zero_error}
                    onChange={(e) =>
                      updateRow(i, "loading_zero_error", e.target.value)
                    }
                    className="w-24 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.unloading_indication}
                    onChange={(e) =>
                      updateRow(i, "unloading_indication", e.target.value)
                    }
                    required
                    className="w-28 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.unloading_additional_load}
                    onChange={(e) =>
                      updateRow(i, "unloading_additional_load", e.target.value)
                    }
                    className="w-24 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.unloading_zero_error}
                    onChange={(e) =>
                      updateRow(i, "unloading_zero_error", e.target.value)
                    }
                    className="w-24 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-xs text-muted-foreground">
        Test load: 10 kg. Required temperature sequence:
        20°C → 40°C → -10°C → 5°C → 20°C.
      </div>
      <Button type="submit" size="sm" disabled={submitting}>
        {submitting ? "Calculating…" : "Run calculation"}
      </Button>
      {error && (
        <p className="text-xs text-status-fail">
          {error}
        </p>
      )}
    </form>
  );
}

function TempNoLoadForm({ onSubmit, submitting, error }) {
  const TEMPERATURES = [20, 40, -10];
  const [rows, setRows] = useState(
    TEMPERATURES.map((temperature) => ({
      temperature,
      zero_error: "",
    }))
  );
  function updateRow(index, value) {
    setRows((current) =>
      current.map((row, i) =>
        i === index
          ? { ...row, zero_error: value }
          : row
      )
    );
  }
  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({
      observations: rows.map((row) => ({
        temperature: Number(row.temperature),
        zero_error: Number(row.zero_error),
      })),
    });
  }
  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="overflow-x-auto rounded-lg border border-input">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b bg-muted/30">
              <th className="px-3 py-2 text-left">
                Temperature (°C)
              </th>
              <th className="px-3 py-2 text-left">
                Zero Error (kg)
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className="border-b last:border-0"
              >
                <td className="px-3 py-2 font-medium">
                  {row.temperature}
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.zero_error}
                    onChange={(e) =>
                      updateRow(i, e.target.value)
                    }
                    required
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-xs text-muted-foreground">
        Required temperature sequence: 20°C → 40°C → -10°C.
      </div>
      <Button
        type="submit"
        size="sm"
        disabled={submitting}
      >
        {submitting ? "Calculating…" : "Run calculation"}
      </Button>
      {error && (
        <p className="text-xs text-status-fail">
          {error}
        </p>
      )}
    </form>
  );
}

function EccentricityForm({ onSubmit, submitting, error }) {
  const POSITIONS = [
    "FRONT_LEFT",
    "FRONT_RIGHT",
    "REAR_LEFT",
    "REAR_RIGHT",
  ];
  const [rows, setRows] = useState(
    POSITIONS.map((position) => ({
      position,
      indication: "",
      additional_load: "0",
      zero_error: "0",
    }))
  );
  function updateRow(index, key, value) {
    setRows((current) =>
      current.map((row, i) =>
        i === index
          ? { ...row, [key]: value }
          : row
      )
    );
  }
  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({
      measurements: rows.map((row) => ({
        position: row.position,
        load: 10,
        indication: Number(row.indication),
        additional_load: Number(row.additional_load || 0),
        zero_error: Number(row.zero_error || 0),
      })),
    });
  }
  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="overflow-x-auto rounded-lg border border-input">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b bg-muted/30">
              <th className="px-3 py-2 text-left">
                Position
              </th>
              <th className="px-3 py-2 text-left">
                Load (kg)
              </th>
              <th className="px-3 py-2 text-left">
                Indication (kg)
              </th>
              <th className="px-3 py-2 text-left">
                Additional Load (kg)
              </th>
              <th className="px-3 py-2 text-left">
                Zero Error (kg)
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={row.position}
                className="border-b last:border-0"
              >
                <td className="px-3 py-2 font-medium">
                  {row.position}
                </td>
                <td className="px-3 py-2">
                  10
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.indication}
                    onChange={(e) =>
                      updateRow(
                        i,
                        "indication",
                        e.target.value
                      )
                    }
                    required
                    className="w-28 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.additional_load}
                    onChange={(e) =>
                      updateRow(
                        i,
                        "additional_load",
                        e.target.value
                      )
                    }
                    className="w-28 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.zero_error}
                    onChange={(e) =>
                      updateRow(
                        i,
                        "zero_error",
                        e.target.value
                      )
                    }
                    className="w-28 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-xs text-muted-foreground">
        Test load: 1/3 Max = 10 kg. Four positions are required.
      </div>
      <Button
        type="submit"
        size="sm"
        disabled={submitting}
      >
        {submitting ? "Calculating…" : "Run calculation"}
      </Button>
      {error && (
        <p className="text-xs text-status-fail">
          {error}
        </p>
      )}
    </form>
  );
}

function RepeatabilityForm({ onSubmit, submitting, error }) {
  const SERIES = [
    {
      series_id: "50_PERCENT_MAX",
      load: 15,
    },
    {
      series_id: "100_PERCENT_MAX",
      load: 30,
    },
  ];
  const [series, setSeries] = useState(
    SERIES.map((item) => ({
      series_id: item.series_id,
      load: item.load,
      measurements: Array.from({ length: 10 }, () => ({
        indication: "",
        additional_load: "0",
      })),
    }))
  );
  function updateMeasurement(seriesIndex, measurementIndex, key, value) {
    setSeries((current) =>
      current.map((item, i) => {
        if (i !== seriesIndex) {
          return item;
        }
        return {
          ...item,
          measurements: item.measurements.map((measurement, j) =>
            j === measurementIndex
              ? { ...measurement, [key]: value }
              : measurement
          ),
        };
      })
    );
  }
  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({
      series: series.map((item) => ({
        series_id: item.series_id,
        measurements: item.measurements.map((measurement) => ({
          load: item.load,
          indication: Number(measurement.indication),
          additional_load: Number(
            measurement.additional_load || 0
          ),
        })),
      })),
    });
  }
  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {series.map((item, seriesIndex) => (
        <div
          key={item.series_id}
          className="rounded-lg border border-input overflow-hidden"
        >
          <div className="border-b bg-muted/30 px-4 py-3">
            <div className="font-medium text-sm">
              {item.series_id === "50_PERCENT_MAX"
                ? "50% Max Load"
                : "100% Max Load"}
            </div>
            <div className="text-xs text-muted-foreground">
              Load: {item.load} kg · 10 measurements
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b">
                  <th className="px-3 py-2 text-left">
                    #
                  </th>
                  <th className="px-3 py-2 text-left">
                    Load (kg)
                  </th>
                  <th className="px-3 py-2 text-left">
                    Indication (kg)
                  </th>
                  <th className="px-3 py-2 text-left">
                    Additional Load (kg)
                  </th>
                </tr>
              </thead>
              <tbody>
                {item.measurements.map((measurement, measurementIndex) => (
                  <tr
                    key={measurementIndex}
                    className="border-b last:border-0"
                  >
                    <td className="px-3 py-2 font-medium">
                      {measurementIndex + 1}
                    </td>
                    <td className="px-3 py-2">
                      {item.load}
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        step="any"
                        value={measurement.indication}
                        onChange={(e) =>
                          updateMeasurement(
                            seriesIndex,
                            measurementIndex,
                            "indication",
                            e.target.value
                          )
                        }
                        required
                        className="w-28 rounded-lg border border-input bg-background px-2 py-2"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        step="any"
                        value={measurement.additional_load}
                        onChange={(e) =>
                          updateMeasurement(
                            seriesIndex,
                            measurementIndex,
                            "additional_load",
                            e.target.value
                          )
                        }
                        className="w-28 rounded-lg border border-input bg-background px-2 py-2"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
      <div className="text-xs text-muted-foreground">
        Two series are required: 50% Max = 15 kg and
        100% Max = 30 kg. Each series contains 10 measurements.
      </div>
      <Button
        type="submit"
        size="sm"
        disabled={submitting}
      >
        {submitting ? "Calculating…" : "Run calculation"}
      </Button>
      {error && (
        <p className="text-xs text-status-fail">
          {error}
        </p>
      )}
    </form>
  );
}

function CreepForm({ onSubmit, submitting, error }) {
  const TIMES = [0, 5, 15, 30];

  const [load, setLoad] = useState("30");

  const [rows, setRows] = useState(
    TIMES.map((time_minutes) => ({
      time_minutes,
      indication: "",
      additional_load: "0",
      temperature: "20",
    }))
  );

  function updateRow(index, key, value) {
    setRows((current) =>
      current.map((row, i) =>
        i === index ? { ...row, [key]: value } : row
      )
    );
  }

  function handleSubmit(e) {
    e.preventDefault();

    onSubmit({
      load: Number(load),
      readings: rows.map((row) => ({
        time_minutes: Number(row.time_minutes),
        indication: Number(row.indication),
        additional_load: Number(row.additional_load || 0),
      })),
      temperatures: rows.map((row) => Number(row.temperature)),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex items-center gap-2">
        <label className="text-xs font-medium">
          Test Load (kg)
        </label>

        <input
          type="number"
          step="any"
          value={load}
          onChange={(e) => setLoad(e.target.value)}
          required
          className="w-32 rounded-lg border border-input bg-background px-3 py-2 text-xs"
        />
      </div>

      <div className="overflow-x-auto rounded-lg border border-input">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b bg-muted/30">
              <th className="px-3 py-2 text-left">
                Time (min)
              </th>
              <th className="px-3 py-2 text-left">
                Indication (kg)
              </th>
              <th className="px-3 py-2 text-left">
                Additional Load (kg)
              </th>
              <th className="px-3 py-2 text-left">
                Temperature (°C)
              </th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b last:border-0">
                <td className="px-3 py-2 font-medium">
                  {row.time_minutes}
                </td>

                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.indication}
                    onChange={(e) =>
                      updateRow(i, "indication", e.target.value)
                    }
                    required
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>

                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.additional_load}
                    onChange={(e) =>
                      updateRow(i, "additional_load", e.target.value)
                    }
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>

                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.temperature}
                    onChange={(e) =>
                      updateRow(i, "temperature", e.target.value)
                    }
                    required
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-muted-foreground">
        Prototype supports the 30-minute early-termination path
        using readings at 0, 5, 15 and 30 minutes.
      </p>

      <Button type="submit" size="sm" disabled={submitting}>
        {submitting ? "Calculating…" : "Run calculation"}
      </Button>

      {error && (
        <p className="text-xs text-status-fail">
          {error}
        </p>
      )}
    </form>
  );
}

function TareForm({ onSubmit, submitting, error }) {
  const [tareValue, setTareValue] = useState("10");
  const [maximumTare, setMaximumTare] = useState("15");

  const [loadingRows, setLoadingRows] = useState(
    Array.from({ length: 5 }, () => ({
      load: "",
      indication: "",
      additional_load: "0",
      zero_error: "0",
    }))
  );

  const [unloadingRows, setUnloadingRows] = useState(
    Array.from({ length: 5 }, () => ({
      load: "",
      indication: "",
      additional_load: "0",
      zero_error: "0",
    }))
  );

  function updateRow(setter, index, key, value) {
    setter((current) =>
      current.map((row, i) =>
        i === index ? { ...row, [key]: value } : row
      )
    );
  }

  function handleSubmit(e) {
    e.preventDefault();

    const convertRows = (rows) =>
      rows.map((row) => ({
        load: Number(row.load),
        indication: Number(row.indication),
        additional_load: Number(row.additional_load || 0),
        zero_error: Number(row.zero_error || 0),
      }));

    onSubmit({
      tare_value: Number(tareValue),
      maximum_tare: Number(maximumTare),
      loading_measurements: convertRows(loadingRows),
      unloading_measurements: convertRows(unloadingRows),
    });
  }

  function renderRows(rows, setter) {
    return rows.map((row, i) => (
      <tr key={i} className="border-b last:border-0">
        <td className="px-3 py-2 font-medium">{i + 1}</td>

        <td className="px-3 py-2">
          <input
            type="number"
            step="any"
            value={row.load}
            onChange={(e) =>
              updateRow(setter, i, "load", e.target.value)
            }
            required
            className="w-28 rounded-lg border border-input bg-background px-2 py-2"
          />
        </td>

        <td className="px-3 py-2">
          <input
            type="number"
            step="any"
            value={row.indication}
            onChange={(e) =>
              updateRow(setter, i, "indication", e.target.value)
            }
            required
            className="w-28 rounded-lg border border-input bg-background px-2 py-2"
          />
        </td>

        <td className="px-3 py-2">
          <input
            type="number"
            step="any"
            value={row.additional_load}
            onChange={(e) =>
              updateRow(setter, i, "additional_load", e.target.value)
            }
            className="w-28 rounded-lg border border-input bg-background px-2 py-2"
          />
        </td>

        <td className="px-3 py-2">
          <input
            type="number"
            step="any"
            value={row.zero_error}
            onChange={(e) =>
              updateRow(setter, i, "zero_error", e.target.value)
            }
            className="w-28 rounded-lg border border-input bg-background px-2 py-2"
          />
        </td>
      </tr>
    ));
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-2 sm:grid-cols-2">
        <div>
          <label className="text-xs font-medium">
            Tare Value (kg)
          </label>
          <input
            type="number"
            step="any"
            value={tareValue}
            onChange={(e) => setTareValue(e.target.value)}
            required
            className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-xs"
          />
        </div>

        <div>
          <label className="text-xs font-medium">
            Maximum Tare (kg)
          </label>
          <input
            type="number"
            step="any"
            value={maximumTare}
            onChange={(e) => setMaximumTare(e.target.value)}
            required
            className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-xs"
          />
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium">
          Loading Measurements
        </p>

        <div className="overflow-x-auto rounded-lg border border-input">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="px-3 py-2 text-left">#</th>
                <th className="px-3 py-2 text-left">Load (kg)</th>
                <th className="px-3 py-2 text-left">Indication (kg)</th>
                <th className="px-3 py-2 text-left">Additional Load (kg)</th>
                <th className="px-3 py-2 text-left">Zero Error (kg)</th>
              </tr>
            </thead>
            <tbody>
              {renderRows(loadingRows, setLoadingRows)}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium">
          Unloading Measurements
        </p>

        <div className="overflow-x-auto rounded-lg border border-input">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="px-3 py-2 text-left">#</th>
                <th className="px-3 py-2 text-left">Load (kg)</th>
                <th className="px-3 py-2 text-left">Indication (kg)</th>
                <th className="px-3 py-2 text-left">Additional Load (kg)</th>
                <th className="px-3 py-2 text-left">Zero Error (kg)</th>
              </tr>
            </thead>
            <tbody>
              {renderRows(unloadingRows, setUnloadingRows)}
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        Enter at least 5 measurements in each direction.
      </p>

      <Button type="submit" size="sm" disabled={submitting}>
        {submitting ? "Calculating…" : "Run calculation"}
      </Button>

      {error && (
        <p className="text-xs text-status-fail">
          {error}
        </p>
      )}
    </form>
  );
}
function WarmupForm({ onSubmit, submitting, error }) {
  const TIMES = [5, 15, 30];

  const [powerOffHours, setPowerOffHours] = useState("8");
  const [load, setLoad] = useState("28");

  const [rows, setRows] = useState(
    TIMES.map((elapsed_minutes) => ({
      elapsed_minutes,
      indication: "",
      zero_error: "0",
      additional_load: "0",
    }))
  );

  function updateRow(index, key, value) {
    setRows((current) =>
      current.map((row, i) =>
        i === index ? { ...row, [key]: value } : row
      )
    );
  }

  function handleSubmit(e) {
    e.preventDefault();

    onSubmit({
      power_off_hours: Number(powerOffHours),
      load: Number(load),
      observations: rows.map((row) => ({
        elapsed_minutes: Number(row.elapsed_minutes),
        indication: Number(row.indication),
        zero_error: Number(row.zero_error || 0),
        additional_load: Number(row.additional_load || 0),
      })),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid gap-2 sm:grid-cols-2">
        <div>
          <label className="text-xs font-medium">
            Power-Off Time (hours)
          </label>
          <input
            type="number"
            step="any"
            value={powerOffHours}
            onChange={(e) => setPowerOffHours(e.target.value)}
            required
            className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-xs"
          />
        </div>

        <div>
          <label className="text-xs font-medium">
            Test Load (kg)
          </label>
          <input
            type="number"
            step="any"
            value={load}
            onChange={(e) => setLoad(e.target.value)}
            required
            className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-xs"
          />
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-input">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b bg-muted/30">
              <th className="px-3 py-2 text-left">
                Elapsed Time (min)
              </th>
              <th className="px-3 py-2 text-left">
                Indication (kg)
              </th>
              <th className="px-3 py-2 text-left">
                Additional Load (kg)
              </th>
              <th className="px-3 py-2 text-left">
                Zero Error (kg)
              </th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b last:border-0">
                <td className="px-3 py-2 font-medium">
                  {row.elapsed_minutes}
                </td>

                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.indication}
                    onChange={(e) =>
                      updateRow(i, "indication", e.target.value)
                    }
                    required
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>

                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.additional_load}
                    onChange={(e) =>
                      updateRow(i, "additional_load", e.target.value)
                    }
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>

                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.zero_error}
                    onChange={(e) =>
                      updateRow(i, "zero_error", e.target.value)
                    }
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-muted-foreground">
        Required observation times: 5, 15 and 30 minutes.
      </p>

      <Button type="submit" size="sm" disabled={submitting}>
        {submitting ? "Calculating…" : "Run calculation"}
      </Button>

      {error && (
        <p className="text-xs text-status-fail">
          {error}
        </p>
      )}
    </form>
  );
}

function VoltageVariationForm({ onSubmit, submitting, error }) {
  const VOLTAGES = [195.5, 230, 253];

  const [load, setLoad] = useState("0.1");

  const [rows, setRows] = useState(
    VOLTAGES.map((voltage) => ({
      voltage,
      indication: "",
      additional_load: "0",
      zero_error: "0",
    }))
  );

  function updateRow(index, key, value) {
    setRows((current) =>
      current.map((row, i) =>
        i === index ? { ...row, [key]: value } : row
      )
    );
  }

  function handleSubmit(e) {
    e.preventDefault();

    onSubmit({
      load: Number(load),
      observations: rows.map((row) => ({
        voltage: Number(row.voltage),
        indication: Number(row.indication),
        additional_load: Number(row.additional_load || 0),
        zero_error: Number(row.zero_error || 0),
      })),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className="text-xs font-medium">Test Load (kg)</label>
        <input
          type="number"
          step="any"
          value={load}
          onChange={(e) => setLoad(e.target.value)}
          required
          className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-xs"
        />
      </div>

      <div className="overflow-x-auto rounded-lg border border-input">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b bg-muted/30">
              <th className="px-3 py-2 text-left">Voltage (V)</th>
              <th className="px-3 py-2 text-left">Indication (kg)</th>
              <th className="px-3 py-2 text-left">
                Additional Load (kg)
              </th>
              <th className="px-3 py-2 text-left">Zero Error (kg)</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b last:border-0">
                <td className="px-3 py-2 font-medium">
                  {row.voltage}
                </td>

                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.indication}
                    onChange={(e) =>
                      updateRow(i, "indication", e.target.value)
                    }
                    required
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>

                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.additional_load}
                    onChange={(e) =>
                      updateRow(i, "additional_load", e.target.value)
                    }
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>

                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.zero_error}
                    onChange={(e) =>
                      updateRow(i, "zero_error", e.target.value)
                    }
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-muted-foreground">
        Required voltages: 195.5 V, 230 V and 253 V.
      </p>

      <Button type="submit" size="sm" disabled={submitting}>
        {submitting ? "Calculating…" : "Run calculation"}
      </Button>

      {error && (
        <p className="text-xs text-status-fail">
          {error}
        </p>
      )}
    </form>
  );
}
function SpanStabilityForm({ onSubmit, submitting, error }) {
  const INITIAL_COUNT = 5;
  const MEASUREMENT_COUNT = 8;

  const [load, setLoad] = useState("28");
  const [powerDisconnections, setPowerDisconnections] = useState(["8", "8"]);

  const [initialRows, setInitialRows] = useState(
    Array.from({ length: INITIAL_COUNT }, () => ({
      indication: "",
      additional_load: "0",
      zero_error: "0",
    }))
  );

  const [measurementRows, setMeasurementRows] = useState(
    Array.from({ length: MEASUREMENT_COUNT }, () => ({
      indication: "",
      additional_load: "0",
      zero_error: "0",
    }))
  );

  function updateRow(setter, index, key, value) {
    setter((current) =>
      current.map((row, i) =>
        i === index ? { ...row, [key]: value } : row
      )
    );
  }

  function handleSubmit(e) {
    e.preventDefault();

    const convertRows = (rows) =>
      rows.map((row) => ({
        indication: Number(row.indication),
        additional_load: Number(row.additional_load || 0),
        zero_error: Number(row.zero_error || 0),
      }));

    onSubmit({
      load: Number(load),

      power_disconnections: powerDisconnections.map((value) =>
        Number(value)
      ),

      initial_readings: convertRows(initialRows),

      measurements: convertRows(measurementRows),
    });
  }

  function renderRows(rows, setter) {
    return rows.map((row, i) => (
      <tr key={i} className="border-b last:border-0">
        <td className="px-3 py-2 font-medium">
          {i + 1}
        </td>

        <td className="px-3 py-2">
          <input
            type="number"
            step="any"
            value={row.indication}
            onChange={(e) =>
              updateRow(
                setter,
                i,
                "indication",
                e.target.value
              )
            }
            required
            className="w-32 rounded-lg border border-input bg-background px-2 py-2"
          />
        </td>

        <td className="px-3 py-2">
          <input
            type="number"
            step="any"
            value={row.additional_load}
            onChange={(e) =>
              updateRow(
                setter,
                i,
                "additional_load",
                e.target.value
              )
            }
            className="w-32 rounded-lg border border-input bg-background px-2 py-2"
          />
        </td>

        <td className="px-3 py-2">
          <input
            type="number"
            step="any"
            value={row.zero_error}
            onChange={(e) =>
              updateRow(
                setter,
                i,
                "zero_error",
                e.target.value
              )
            }
            className="w-32 rounded-lg border border-input bg-background px-2 py-2"
          />
        </td>
      </tr>
    ));
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-2 sm:grid-cols-3">
        <div>
          <label className="text-xs font-medium">
            Test Load (kg)
          </label>

          <input
            type="number"
            step="any"
            value={load}
            onChange={(e) => setLoad(e.target.value)}
            required
            className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-xs"
          />
        </div>

        <div>
          <label className="text-xs font-medium">
            Power Disconnection 1 (hours)
          </label>

          <input
            type="number"
            step="any"
            min="8"
            value={powerDisconnections[0]}
            onChange={(e) =>
              setPowerDisconnections((current) => [
                e.target.value,
                current[1],
              ])
            }
            required
            className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-xs"
          />
        </div>

        <div>
          <label className="text-xs font-medium">
            Power Disconnection 2 (hours)
          </label>

          <input
            type="number"
            step="any"
            min="8"
            value={powerDisconnections[1]}
            onChange={(e) =>
              setPowerDisconnections((current) => [
                current[0],
                e.target.value,
              ])
            }
            required
            className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-xs"
          />
        </div>
      </div>

      <div>
        <h4 className="mb-2 text-sm font-semibold">
          Initial Readings — 5
        </h4>

        <div className="overflow-x-auto rounded-lg border border-input">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="px-3 py-2 text-left">Reading</th>
                <th className="px-3 py-2 text-left">
                  Indication (kg)
                </th>
                <th className="px-3 py-2 text-left">
                  Additional Load (kg)
                </th>
                <th className="px-3 py-2 text-left">
                  Zero Error (kg)
                </th>
              </tr>
            </thead>

            <tbody>
              {renderRows(initialRows, setInitialRows)}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h4 className="mb-2 text-sm font-semibold">
          Subsequent Measurements — 8
        </h4>

        <div className="overflow-x-auto rounded-lg border border-input">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="px-3 py-2 text-left">Reading</th>
                <th className="px-3 py-2 text-left">
                  Indication (kg)
                </th>
                <th className="px-3 py-2 text-left">
                  Additional Load (kg)
                </th>
                <th className="px-3 py-2 text-left">
                  Zero Error (kg)
                </th>
              </tr>
            </thead>

            <tbody>
              {renderRows(measurementRows, setMeasurementRows)}
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        Required: 5 initial readings, at least 8 subsequent
        measurements, and two power disconnections of at least
        8 hours each.
      </p>

      <Button type="submit" size="sm" disabled={submitting}>
        {submitting ? "Calculating…" : "Run calculation"}
      </Button>

      {error && (
        <p className="text-xs text-status-fail">
          {error}
        </p>
      )}
    </form>
  );
}

// TODO:
function DiscriminationForm({ onSubmit, submitting, error }) {
  const LOADS = [0.2, 15, 30];

  const [rows, setRows] = useState(
    LOADS.map((load) => ({
      load,
      initial_indication: "",
      decreased_indication: "",
      increased_indication: "",
    }))
  );

  function updateRow(index, key, value) {
    setRows((current) =>
      current.map((row, i) =>
        i === index ? { ...row, [key]: value } : row
      )
    );
  }

  function handleSubmit(e) {
    e.preventDefault();

    onSubmit({
      loads: rows.map((row) => ({
        load: Number(row.load),
        initial_indication: Number(row.initial_indication),
        decreased_indication: Number(row.decreased_indication),
        increased_indication: Number(row.increased_indication),
      })),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="overflow-x-auto rounded-lg border border-input">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b bg-muted/30">
              <th className="px-3 py-2 text-left">Load (kg)</th>
              <th className="px-3 py-2 text-left">Initial Indication (kg)</th>
              <th className="px-3 py-2 text-left">Decreased Indication (kg)</th>
              <th className="px-3 py-2 text-left">Increased Indication (kg)</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b last:border-0">
                <td className="px-3 py-2 font-medium">
                  {row.load}
                </td>

                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.initial_indication}
                    onChange={(e) =>
                      updateRow(i, "initial_indication", e.target.value)
                    }
                    required
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>

                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.decreased_indication}
                    onChange={(e) =>
                      updateRow(i, "decreased_indication", e.target.value)
                    }
                    required
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>

                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    value={row.increased_indication}
                    onChange={(e) =>
                      updateRow(i, "increased_indication", e.target.value)
                    }
                    required
                    className="w-32 rounded-lg border border-input bg-background px-2 py-2"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-muted-foreground">
        Required loads: Min = 0.2 kg, Max/2 = 15 kg, Max = 30 kg.
      </p>

      <Button type="submit" size="sm" disabled={submitting}>
        {submitting ? "Calculating…" : "Run calculation"}
      </Button>

      {error && (
        <p className="text-xs text-status-fail">
          {error}
        </p>
      )}
    </form>
  );
}

function GenericJsonForm({ testCode, onSubmit, submitting, error }) {
  const template = TEST_INPUT_TEMPLATES[testCode];
  const [text, setText] = useState(template ? JSON.stringify(template, null, 2) : "{\n  \n}");
  const [parseError, setParseError] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    setParseError("");
    try {
      const parsed = JSON.parse(text);
      onSubmit(parsed);
    } catch (err) {
      setParseError("Invalid JSON: " + err.message);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      {!template && (
        <p className="text-xs text-status-pending">
          No template available for test code "{testCode}" — check the engine source for its expected shape.
        </p>
      )}
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={Math.min(16, text.split("\n").length + 1)}
        className="w-full rounded-lg border border-input bg-background px-3 py-2 font-mono text-xs outline-none focus:ring-2 focus:ring-ring"
      />
      <Button type="submit" size="sm" disabled={submitting}>{submitting ? "Calculating…" : "Run calculation"}</Button>
      {(parseError || error) && <p className="text-xs text-status-fail">{parseError || error}</p>}
    </form>
  );
}

function CalculationResultView({
  testCode,
  result,
}) {
  const calculations =
    result?.details?.calculations;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 rounded-lg bg-muted/50 p-3 text-xs sm:grid-cols-4">
        <span>
          Measured:{" "}
          <span className="font-num">
            {result.measured_value ?? "—"}
          </span>
        </span>
        <span>
          MPE:{" "}
          <span className="font-num">
            {result.mpe_value ?? "—"}
          </span>
        </span>
        <span>
          Error:{" "}
          <span className="font-num">
            {result.error_value ?? "—"}
          </span>
        </span>
        <span>
          Result:{" "}
          <span className="font-num">
            {result.pass_fail ?? "—"}
          </span>
        </span>
        {result.result_summary && (
          <span className="col-span-full text-muted-foreground">
            {result.result_summary}
          </span>
        )}
      </div>
      {testCode === "WP" &&
        Array.isArray(calculations) &&
        calculations.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full min-w-[900px] text-xs">
              <thead className="bg-muted/50">
                <tr className="border-b border-border text-left">
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">
                    Load (kg)
                  </th>
                  <th className="px-3 py-2">
                    Indication (kg)
                  </th>
                  <th className="px-3 py-2">
                    Additional Load (kg)
                  </th>
                  <th className="px-3 py-2">
                    True Value (kg)
                  </th>
                  <th className="px-3 py-2">
                    Error (kg)
                  </th>
                  <th className="px-3 py-2">
                    Corrected Error (kg)
                  </th>
                  <th className="px-3 py-2">
                    MPE (kg)
                  </th>
                  <th className="px-3 py-2">
                    Result
                  </th>
                </tr>
              </thead>
              <tbody>
                {calculations.map((calculation) => (
                  <tr
                    key={calculation.sequence_no}
                    className="border-b border-border last:border-b-0"
                  >
                    <td className="px-3 py-2 font-num">
                      {calculation.sequence_no}
                    </td>
                    <td className="px-3 py-2 font-num">
                      {calculation.load ?? "—"}
                    </td>
                    <td className="px-3 py-2 font-num">
                      {calculation.indication ?? "—"}
                    </td>
                    <td className="px-3 py-2 font-num">
                      {calculation.additional_load ?? "—"}
                    </td>
                    <td className="px-3 py-2 font-num">
                      {calculation.conventional_true_value ??
                        "—"}
                    </td>
                    <td className="px-3 py-2 font-num">
                      {calculation.error ?? "—"}
                    </td>
                    <td className="px-3 py-2 font-num">
                      {calculation.corrected_error ?? "—"}
                    </td>
                    <td className="px-3 py-2 font-num">
                      {calculation.mpe ?? "—"}
                    </td>
                    <td className="px-3 py-2 font-medium">
                      {calculation.pass
                        ? "PASS"
                        : "FAIL"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
    </div>
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
      const created = await api.addTestToSession(sessionId, values, token);
      reset({ applicability_status: "APPLICABLE" });
      onAdded(created);
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

function SessionTestCard({ test, token, canEnter, canCalculate, onObservationAdded, onCalculationSaved }) {
  const [obsError, setObsError] = useState("");
  const obsForm = useForm();
  const hasResult = test.results && test.results.length > 0;
  const latestResult = hasResult ? test.results[test.results.length - 1] : null;

  async function onAddObservation(values) {
    setObsError("");
    try {
      const payload = {
        ...values,
        value_numeric: values.value_numeric === "" ? undefined : Number(values.value_numeric),
      };
      const created = await api.addObservation(test.session_test_id, payload, token);
      obsForm.reset();
      onObservationAdded(test.session_test_id, created);
    } catch (err) {
      setObsError(err.message);
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
                {test.observations?.length > 0 ? (
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
                ) : (
                  !canEnter && <p className="text-xs text-muted-foreground">No readings were recorded.</p>
                )}
                {canEnter && (
                  <>
                    <form onSubmit={obsForm.handleSubmit(onAddObservation)} className="grid gap-2 sm:grid-cols-[1fr_auto_auto_auto]">
                      <input placeholder="Parameter (e.g. Indicated value)" {...obsForm.register("parameter_name", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-xs" />
                      <input type="number" step="any" placeholder="Value" {...obsForm.register("value_numeric")} className="w-24 rounded-lg border border-input bg-background px-3 py-2 text-xs" />
                      <input placeholder="Unit" {...obsForm.register("unit")} className="w-20 rounded-lg border border-input bg-background px-3 py-2 text-xs" />
                      <Button type="submit" size="sm" aria-label="Add reading"><Plus className="h-3.5 w-3.5" /></Button>
                    </form>
                    {obsError && <p className="mt-1 text-xs text-status-fail">{obsError}</p>}
                  </>
                )}
              </div>

              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Calculation {latestResult && "(computed by R76 engine)"}
                </p>
                {latestResult ? (
                  <CalculationResultView testCode={test.test_code} result={latestResult} />
                ) : canCalculate ? (
                  <CalculationForm
                    sessionTestId={test.session_test_id}
                    testCode={test.test_code}
                    token={token}
                    onSaved={(result) => onCalculationSaved(test.session_test_id, result)}
                  />
                ) : (
                  <p className="text-xs text-muted-foreground">Not calculated yet. The tester runs the calculation.</p>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
