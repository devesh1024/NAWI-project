import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/apiClient";

const TABS = ["Standards", "Test Definitions", "Applicability Rules", "MPE Rules"];
const ACCURACY_CLASSES = ["I", "II", "III", "IIII"];

export default function Standards() {
  const { token } = useAuth();
  const [tab, setTab] = useState(0);
  const [standards, setStandards] = useState([]);
  const [testDefinitions, setTestDefinitions] = useState([]);
  const [applicabilityRules, setApplicabilityRules] = useState([]);
  const [mpeRules, setMpeRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  async function loadAll() {
    setLoading(true);
    setLoadError("");
    try {
      const [s, td, ar, mpe] = await Promise.all([
        api.getStandards(token),
        api.getTestDefinitions(token),
        api.getApplicabilityRules(token),
        api.getMpeRules(token),
      ]);
      setStandards(s);
      setTestDefinitions(td);
      setApplicabilityRules(ar);
      setMpeRules(mpe);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) loadAll();
  }, [token]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Standards & Rules</h1>
        <p className="text-sm text-muted-foreground">
          Reference data: standards, applicable tests, applicability conditions and MPE thresholds.
        </p>
      </div>

      <div className="flex gap-1 rounded-lg border border-border bg-surface p-1 w-fit">
        {TABS.map((t, i) => (
          <button
            key={t}
            onClick={() => setTab(i)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === i ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
            }`}
            data-cursor-hover
          >
            {t}
          </button>
        ))}
      </div>

      {loading && <p className="py-6 text-center text-sm text-muted-foreground">Loading…</p>}
      {loadError && <p className="py-6 text-center text-sm text-status-fail">{loadError}</p>}

      {!loading && !loadError && (
        <>
          {tab === 0 && <StandardsTab token={token} data={standards} onSaved={loadAll} />}
          {tab === 1 && (
            <TestDefinitionsTab token={token} data={testDefinitions} standards={standards} onSaved={loadAll} />
          )}
          {tab === 2 && (
            <ApplicabilityRulesTab
              token={token}
              data={applicabilityRules}
              testDefinitions={testDefinitions}
              onSaved={loadAll}
            />
          )}
          {tab === 3 && <MpeRulesTab token={token} data={mpeRules} standards={standards} onSaved={loadAll} />}
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

function TabShell({ title, onAdd, children }) {
  const { can } = useAuth();
  const canManage = can("methods.manage");

  return (
    <Card>
      <CardContent className="pt-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-muted-foreground">{title}</h2>
          {canManage ? (
            <Button size="sm" onClick={onAdd}>
              <Plus className="h-4 w-4" /> Add
            </Button>
          ) : (
            <span className="text-xs text-muted-foreground">Read-only · maintained by the Lab Head and Technical Manager</span>
          )}
        </div>
        {children}
      </CardContent>
    </Card>
  );
}

function StandardsTab({ token, data, onSaved }) {
  const [showForm, setShowForm] = useState(false);
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm();

  async function onSubmit(values) {
    const payload = Object.fromEntries(Object.entries(values).filter(([, v]) => v !== ""));
    await api.createStandard(payload, token);
    reset();
    setShowForm(false);
    onSaved();
  }

  return (
    <TabShell title={`${data.length} standard(s)`} onAdd={() => setShowForm((s) => !s)}>
      {showForm && (
        <form onSubmit={handleSubmit(onSubmit)} className="mb-4 grid gap-3 rounded-lg border border-border p-4 sm:grid-cols-2">
          <input placeholder="Standard code (e.g. OIML-R76-1)" {...register("standard_code", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <input placeholder="Title" {...register("title", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <input placeholder="Version" {...register("version")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <input type="number" placeholder="Edition year" {...register("edition_year")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <Button type="submit" size="sm" disabled={isSubmitting} className="sm:col-span-2">
            {isSubmitting ? "Saving…" : "Save standard"}
          </Button>
        </form>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            <th className="pb-2 font-medium">Code</th>
            <th className="pb-2 font-medium">Title</th>
            <th className="pb-2 font-medium">Version</th>
            <th className="pb-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {data.map((s) => (
            <tr key={s.standard_id} className="border-t border-border">
              <td className="py-2 font-num text-xs">{s.standard_code}</td>
              <td className="py-2">{s.title}</td>
              <td className="py-2 text-muted-foreground">{s.version || "—"}</td>
              <td className="py-2 text-muted-foreground">{s.status || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TabShell>
  );
}

function TestDefinitionsTab({ token, data, standards, onSaved }) {
  const [showForm, setShowForm] = useState(false);
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm();

  async function onSubmit(values) {
    const payload = { ...values, is_mandatory: values.is_mandatory === "true" };
    await api.createTestDefinition(payload, token);
    reset();
    setShowForm(false);
    onSaved();
  }

  return (
    <TabShell title={`${data.length} test definition(s)`} onAdd={() => setShowForm((s) => !s)}>
      {showForm && (
        <form onSubmit={handleSubmit(onSubmit)} className="mb-4 grid gap-3 rounded-lg border border-border p-4 sm:grid-cols-2">
          <select {...register("standard_id", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm sm:col-span-2">
            <option value="">Select standard…</option>
            {standards.map((s) => (
              <option key={s.standard_id} value={s.standard_id}>{s.standard_code} — {s.title}</option>
            ))}
          </select>
          <input placeholder="Test code (e.g. 3.1)" {...register("test_code", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <input placeholder="Test name" {...register("test_name", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <input placeholder="Category" {...register("category")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <select {...register("is_mandatory")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm">
            <option value="true">Mandatory</option>
            <option value="false">Optional</option>
          </select>
          <Button type="submit" size="sm" disabled={isSubmitting} className="sm:col-span-2">
            {isSubmitting ? "Saving…" : "Save test definition"}
          </Button>
        </form>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            <th className="pb-2 font-medium">Code</th>
            <th className="pb-2 font-medium">Name</th>
            <th className="pb-2 font-medium">Category</th>
            <th className="pb-2 font-medium">Mandatory</th>
          </tr>
        </thead>
        <tbody>
          {data.map((t) => (
            <tr key={t.test_definition_id} className="border-t border-border">
              <td className="py-2 font-num text-xs">{t.test_code}</td>
              <td className="py-2">{t.test_name}</td>
              <td className="py-2 text-muted-foreground">{t.category || "—"}</td>
              <td className="py-2 text-muted-foreground">{t.is_mandatory ? "Yes" : "No"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TabShell>
  );
}

function ApplicabilityRulesTab({ token, data, testDefinitions, onSaved }) {
  const [showForm, setShowForm] = useState(false);
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm();

  async function onSubmit(values) {
    const payload = { ...values, applicable: values.applicable === "true" };
    await api.createApplicabilityRule(payload, token);
    reset();
    setShowForm(false);
    onSaved();
  }

  function testName(id) {
    const t = testDefinitions.find((t) => t.test_definition_id === id);
    return t ? `${t.test_code} — ${t.test_name}` : id;
  }

  return (
    <TabShell title={`${data.length} rule(s)`} onAdd={() => setShowForm((s) => !s)}>
      {showForm && (
        <form onSubmit={handleSubmit(onSubmit)} className="mb-4 grid gap-3 rounded-lg border border-border p-4 sm:grid-cols-2">
          <select {...register("test_definition_id", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm sm:col-span-2">
            <option value="">Select test…</option>
            {testDefinitions.map((t) => (
              <option key={t.test_definition_id} value={t.test_definition_id}>{t.test_code} — {t.test_name}</option>
            ))}
          </select>
          <select {...register("applicable", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm">
            <option value="true">Applicable</option>
            <option value="false">Not applicable</option>
          </select>
          <input type="number" placeholder="Priority" {...register("priority")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <input placeholder="Reason (e.g. why N/A)" {...register("reason")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm sm:col-span-2" />
          <Button type="submit" size="sm" disabled={isSubmitting} className="sm:col-span-2">
            {isSubmitting ? "Saving…" : "Save rule"}
          </Button>
        </form>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            <th className="pb-2 font-medium">Test</th>
            <th className="pb-2 font-medium">Applicable</th>
            <th className="pb-2 font-medium">Reason</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r) => (
            <tr key={r.applicability_rule_id} className="border-t border-border">
              <td className="py-2">{testName(r.test_definition_id)}</td>
              <td className="py-2">{r.applicable ? "Yes" : "No"}</td>
              <td className="py-2 text-muted-foreground">{r.reason || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TabShell>
  );
}

function MpeRulesTab({ token, data, standards, onSaved }) {
  const [showForm, setShowForm] = useState(false);
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm();

  async function onSubmit(values) {
    const payload = Object.fromEntries(Object.entries(values).filter(([, v]) => v !== ""));
    await api.createMpeRule(payload, token);
    reset();
    setShowForm(false);
    onSaved();
  }

  return (
    <TabShell title={`${data.length} MPE rule(s)`} onAdd={() => setShowForm((s) => !s)}>
      {/* These are the load-band rows from OIML R-76 Table 6 — accuracy
          class + e-range -> ±0.5e / ±1.0e / ±1.5e. See the OIML research
          notes shared earlier in the project for the real values to enter. */}
      {showForm && (
        <form onSubmit={handleSubmit(onSubmit)} className="mb-4 grid gap-3 rounded-lg border border-border p-4 sm:grid-cols-2">
          <select {...register("standard_id", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm sm:col-span-2">
            <option value="">Select standard…</option>
            {standards.map((s) => (
              <option key={s.standard_id} value={s.standard_id}>{s.standard_code} — {s.title}</option>
            ))}
          </select>
          <select {...register("accuracy_class", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm">
            <option value="">Accuracy class…</option>
            {ACCURACY_CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <input placeholder="Condition (optional)" {...register("condition")} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <input type="number" step="any" placeholder="Range min (in e)" {...register("range_min_e", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <input type="number" step="any" placeholder="Range max (in e)" {...register("range_max_e", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <input type="number" step="any" placeholder="MPE value (× e, e.g. 0.5)" {...register("mpe_value_e", { required: true })} className="rounded-lg border border-input bg-background px-3 py-2 text-sm sm:col-span-2" />
          <Button type="submit" size="sm" disabled={isSubmitting} className="sm:col-span-2">
            {isSubmitting ? "Saving…" : "Save MPE rule"}
          </Button>
        </form>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            <th className="pb-2 font-medium">Class</th>
            <th className="pb-2 font-medium">Range (in e)</th>
            <th className="pb-2 font-medium">MPE</th>
          </tr>
        </thead>
        <tbody>
          {data.map((m) => (
            <tr key={m.mpe_rule_id} className="border-t border-border">
              <td className="py-2 font-num">{m.accuracy_class}</td>
              <td className="py-2 font-num text-xs text-muted-foreground">{m.range_min_e} – {m.range_max_e}</td>
              <td className="py-2 font-num">±{m.mpe_value_e}e</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TabShell>
  );
}
