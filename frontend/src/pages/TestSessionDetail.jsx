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
import { TEST_INPUT_TEMPLATES, DEDICATED_FORM_TEST_CODES } from "@/lib/calculationTemplates";

const STATUS_FLOW = ["DRAFT", "IN PROGRESS", "SUBMITTED", "UNDER REVIEW", "APPROVED", "REJECTED"];
// Only these roles can approve, per the backend's require_lab_admin /
// reviewer check on PATCH .../approve-report — TODO: confirm exact role
// set with backend if this changes.
const APPROVER_ROLES = ["LAB_ADMIN", "REVIEWER"];

function resultBadge(pass_fail) {
  if (pass_fail === "PASS") return "pass";
  if (pass_fail === "FAIL") return "fail";
  if (pass_fail === "N/A") return "na";
  return "pending";
}

export default function TestSessionDetail() {
  const { id } = useParams();
  const { token, role } = useAuth();

  const [session, setSession] = useState(null);
  // `tests` is seeded from report-data on load, then mutated locally as
  // tests/observations/calculations are added — see handleTestAdded /
  // handleObservationAdded / handleCalculationSaved below. This is what
  // avoids a full page/session reload after every single add: only this
  // array updates, via the exact object the API just returned, no refetch.
  const [tests, setTests] = useState([]);
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
        // calculations/results, so it's used once here to seed local state.
        api.getReportData(id, token).catch(() => null),
        api.getTestDefinitions(token),
      ]);
      setSession(s);
      setTests(rd?.tests || []);
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

  // Called with the raw TestSessionTestResponse from POST .../tests.
  // Enriched with test_code/test_name/category from testDefinitions (which
  // report-data's join normally provides) so SessionTestCard can render it
  // identically to a server-seeded test, with no refetch.
  function handleTestAdded(newSessionTest) {
    const def = testDefinitions.find((t) => t.test_definition_id === newSessionTest.test_definition_id);
    setTests((prev) => [
      ...prev,
      {
        ...newSessionTest,
        test_code: def?.test_code,
        test_name: def?.test_name,
        category: def?.category,
        observations: [],
        results: [],
      },
    ]);
  }

  // Called with the raw ObservationResponse from POST .../observations.
  function handleObservationAdded(sessionTestId, observation) {
    setTests((prev) =>
      prev.map((t) =>
        t.session_test_id === sessionTestId
          ? { ...t, observations: [...(t.observations || []), observation] }
          : t
      )
    );
  }

  // Called with the `result` object from POST .../calculation-result's
  // response (already shaped like a TestResult row — see CalculationForm).
  function handleCalculationSaved(sessionTestId, result) {
    setTests((prev) =>
      prev.map((t) =>
        t.session_test_id === sessionTestId
          ? { ...t, result: result.pass_fail, results: [...(t.results || []), result] }
          : t
      )
    );
  }

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

  async function handleSubmitForReview() {
    setActionError("");
    setBusy(true);

    try {
      await api.updateTestSessionStatus(
        id,
        "SUBMITTED",
        token
      );
      await load();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmitForApproval() {
    setActionError("");
    setBusy(true);

    try {
      await api.submitReportForApproval(id, token);
      await load();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
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

      <AddTestPanel sessionId={id} token={token} testDefinitions={testDefinitions} onAdded={handleTestAdded} />

      <div className="space-y-4">
        {tests.map((t) => (
          <SessionTestCard
            key={t.session_test_id}
            test={t}
            token={token}
            onObservationAdded={handleObservationAdded}
            onCalculationSaved={handleCalculationSaved}
          />
        ))}
        {tests.length === 0 && (
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
          {role === "TESTER" && session?.status === "IN PROGRESS" && (
            <Button onClick={handleSubmitForReview} disabled={busy}>
              <CheckCircle2 className="h-4 w-4" /> Submit for Review
            </Button>
          )}

          {role === "REVIEWER" && session?.status === "SUBMITTED" && (
            <Button onClick={async () => {
              setActionError("");
              setBusy(true);

              try {
                await api.updateTestSessionStatus(id, "UNDER REVIEW", token);
                await load();
              } catch (err) {
                setActionError(err.message);
              } finally {
                setBusy(false);
              }
            }} disabled={busy}>
              <CheckCircle2 className="h-4 w-4" /> Start Review
            </Button>
          )}

          {role === "REVIEWER" && session?.status === "UNDER REVIEW" && (
            <Button onClick={handleSubmitForApproval} disabled={busy}>
              <CheckCircle2 className="h-4 w-4" /> Submit for Approval
            </Button>
          )}

          {role === "APPROVER" && report?.report_status === "PENDING_APPROVAL" && (
            <>
              <Button
                variant="accent"
                onClick={handleApprove}
                disabled={busy}
              >
                <CheckCircle2 className="h-4 w-4" /> Approve Report
              </Button>

              <Button
                variant="destructive"
                onClick={async () => {
                  setActionError("");
                  setBusy(true);

                  try {
                    await api.approveReport(id, token, "REJECT");
                    await load();
                  } catch (err) {
                    setActionError(err.message);
                  } finally {
                    setBusy(false);
                  }
                }}
                disabled={busy}
              >
                Reject Report
              </Button>
            </>
          )}

          {role === "LAB_ADMIN" && (
            <Button
              variant="accent"
              onClick={handleApprove}
              disabled={busy}
            >
              <CheckCircle2 className="h-4 w-4" /> Approve Report
            </Button>
          )}

          <Button onClick={handleGenerateReport} disabled={busy}>
            <FileDown className="h-4 w-4" /> Generate report (DOCX)
          </Button>

          <Button variant="secondary" onClick={() => handleDownload("pdf")}>
            <FileDown className="h-4 w-4" /> Download PDF
          </Button>

          <Button variant="secondary" onClick={() => handleDownload("docx")}>
            <FileDown className="h-4 w-4" /> Download DOCX
          </Button>
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

/**
 * Submits { inputs: {...} } to POST .../calculation-result — the backend's
 * R76 engine computes measured_value/mpe_value/error_value/pass_fail
 * itself now (see backend/app/services/calculation_engine/). WP and ZR get
 * dedicated forms since their shapes are simple and representative; every
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

function SessionTestCard({ test, token, onObservationAdded, onCalculationSaved }) {
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
                  Calculation {latestResult && "(computed by R76 engine)"}
                </p>
                {latestResult ? (
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 rounded-lg bg-muted/50 p-3 text-xs sm:grid-cols-4">
                    <span>Measured: <span className="font-num">{latestResult.measured_value ?? "—"}</span></span>
                    <span>MPE: <span className="font-num">{latestResult.mpe_value ?? "—"}</span></span>
                    <span>Error: <span className="font-num">{latestResult.error_value ?? "—"}</span></span>
                    <span>Result: <span className="font-num">{latestResult.pass_fail ?? "—"}</span></span>
                    {latestResult.result_summary && (
                      <span className="col-span-full text-muted-foreground">{latestResult.result_summary}</span>
                    )}
                  </div>
                ) : (
                  <CalculationForm
                    sessionTestId={test.session_test_id}
                    testCode={test.test_code}
                    token={token}
                    onSaved={(result) => onCalculationSaved(test.session_test_id, result)}
                  />
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
