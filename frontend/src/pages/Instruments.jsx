import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useForm } from "react-hook-form";
import { Search, Plus, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { RowActions } from "@/components/ui/RowActions";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/apiClient";

// Mirrors backend/app/schemas/instrument.py::InstrumentCreate exactly.
const NEW_INSTRUMENT_FIELDS = [
  ["instrument_code", "Instrument code", true],
  ["manufacturer", "Manufacturer"],
  ["model", "Model"],
  ["type_designation", "Type designation"],
  ["serial_number", "Serial number"],
  ["instrument_type", "Instrument type"],
  ["category", "Category"],
  ["accuracy_class", "Accuracy class (I / II / III / IIII)"],
  ["max_capacity", "Max capacity", false, "number"],
  ["min_capacity", "Min capacity", false, "number"],
  ["verification_scale_interval", "Verification scale interval (e)", false, "number"],
  ["scale_interval", "Scale interval (d)", false, "number"],
  ["number_of_intervals", "Number of intervals (n)", false, "number"],
  ["unit", "Unit"],
];

// Empty form: every key present, so reset() fully clears a previous edit.
const EMPTY_VALUES = {
  ...Object.fromEntries(NEW_INSTRUMENT_FIELDS.map(([key]) => [key, ""])),
  status: "ACTIVE",
};

function toFormValues(inst) {
  return {
    ...Object.fromEntries(NEW_INSTRUMENT_FIELDS.map(([key]) => [key, inst[key] ?? ""])),
    status: (inst.status || "ACTIVE").toUpperCase(),
  };
}

export default function Instruments() {
  const { token, can } = useAuth();
  const canRegister = can("instruments.register");
  const canDelete = can("instruments.delete");
  const [instruments, setInstruments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [query, setQuery] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [editing, setEditing] = useState(null); // instrument being edited, null = registering
  const [actionError, setActionError] = useState("");
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm();

  async function loadInstruments() {
    setLoading(true);
    setLoadError("");
    try {
      const data = await api.getInstruments(token);
      setInstruments(data);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) loadInstruments();
  }, [token]);

  function openCreate() {
    setEditing(null);
    setSubmitError("");
    reset(EMPTY_VALUES);
    setShowForm(true);
  }

  function openEdit(inst) {
    setEditing(inst);
    setSubmitError("");
    reset(toFormValues(inst));
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditing(null);
  }

  async function handleDelete(inst) {
    const label = [inst.instrument_code, inst.manufacturer, inst.model].filter(Boolean).join(" ");
    if (!window.confirm(`Delete instrument ${label}?\n\nThis cannot be undone.`)) return;
    setActionError("");
    try {
      await api.deleteInstrument(inst.instrument_id, token);
      loadInstruments();
    } catch (err) {
      setActionError(err.message); // e.g. "used by N test session(s)... set INACTIVE instead"
    }
  }

  async function onSubmit(values) {
    setSubmitError("");
    const numeric = (k) => NEW_INSTRUMENT_FIELDS.find(([key]) => key === k)?.[3] === "number";

    try {
      if (editing) {
        // The code is the instrument's identity and is not editable. A cleared
        // field is sent as null so it really is cleared on the server.
        const payload = Object.fromEntries(
          Object.entries(values)
            .filter(([k]) => k !== "instrument_code")
            .map(([k, v]) => [k, v === "" ? null : numeric(k) ? Number(v) : v])
        );
        await api.updateInstrument(editing.instrument_id, payload, token);
      } else {
        // Cast the number fields (native inputs give strings); drop empties.
        const payload = Object.fromEntries(
          Object.entries(values)
            .filter(([k, v]) => v !== "" && k !== "status")
            .map(([k, v]) => [k, numeric(k) ? Number(v) : v])
        );
        await api.createInstrument(payload, token);
      }
      reset(EMPTY_VALUES);
      closeForm();
      loadInstruments();
    } catch (err) {
      setSubmitError(err.message);
    }
  }

  const filtered = instruments.filter((i) =>
    `${i.manufacturer || ""} ${i.model || ""} ${i.instrument_type || ""}`
      .toLowerCase()
      .includes(query.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Instruments</h1>
          <p className="text-sm text-muted-foreground">Master data for every instrument submitted to your lab.</p>
        </div>
        {canRegister && (
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" /> Register instrument
          </Button>
        )}
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search manufacturer, model, type…"
          className="w-full rounded-lg border border-input bg-surface py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      {actionError && (
        <p className="rounded-lg bg-status-fail/10 px-3 py-2 text-sm text-status-fail">{actionError}</p>
      )}

      <Card>
        <CardContent className="pt-5">
          {loading && <p className="py-6 text-center text-sm text-muted-foreground">Loading instruments…</p>}
          {loadError && <p className="py-6 text-center text-sm text-status-fail">{loadError}</p>}
          {!loading && !loadError && filtered.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No instruments yet — register your first one.
            </p>
          )}
          {!loading && !loadError && filtered.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="pb-2 font-medium">Code</th>
                  <th className="pb-2 font-medium">Manufacturer</th>
                  <th className="pb-2 font-medium">Model</th>
                  <th className="pb-2 font-medium">Type</th>
                  <th className="pb-2 font-medium">Accuracy class</th>
                  <th className="pb-2 font-medium">Max / Min / e</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((inst, i) => (
                  <motion.tr
                    key={inst.instrument_id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="cursor-pointer border-t border-border hover:bg-muted/50"
                    data-cursor-hover
                  >
                    <td className="py-2.5 font-num text-xs">{inst.instrument_code}</td>
                    <td className="py-2.5 font-medium">{inst.manufacturer || "—"}</td>
                    <td className="py-2.5">{inst.model || "—"}</td>
                    <td className="py-2.5 text-muted-foreground">{inst.instrument_type || "—"}</td>
                    <td className="py-2.5 font-num">{inst.accuracy_class || "—"}</td>
                    <td className="py-2.5 font-num text-xs text-muted-foreground">
                      {inst.max_capacity ?? "—"} / {inst.min_capacity ?? "—"} / {inst.verification_scale_interval ?? "—"}
                    </td>
                    <td className="py-2.5">
                      <span
                        className={
                          "rounded-full px-2 py-0.5 text-xs font-medium " +
                          ((inst.status || "").toUpperCase() === "INACTIVE"
                            ? "bg-muted text-muted-foreground"
                            : "bg-status-pass/10 text-status-pass")
                        }
                      >
                        {inst.status || "active"}
                      </span>
                    </td>
                    <td className="py-2.5">
                      {(canRegister || canDelete) && (
                        <RowActions onEdit={canRegister ? () => openEdit(inst) : null} onDelete={canDelete ? () => handleDelete(inst) : null} />
                      )}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
            onClick={closeForm}
          >
            <motion.div
              initial={{ opacity: 0, y: 16, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.98 }}
              transition={{ type: "spring", stiffness: 320, damping: 28 }}
              onClick={(e) => e.stopPropagation()}
              className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-border bg-surface p-6 shadow-raised"
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-heading text-lg font-semibold">
                  {editing ? `Edit instrument — ${editing.instrument_code}` : "Register instrument"}
                </h2>
                <button type="button" onClick={closeForm} data-cursor-hover>
                  <X className="h-5 w-5 text-muted-foreground" />
                </button>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="grid gap-3 sm:grid-cols-2">
                {NEW_INSTRUMENT_FIELDS.map(([key, label, required, type]) => (
                  <div key={key}>
                    <label className="text-sm font-medium">
                      {label}
                      {required && <span className="text-status-fail"> *</span>}
                    </label>
                    <input
                      type={type === "number" ? "number" : "text"}
                      step={type === "number" ? "any" : undefined}
                      readOnly={Boolean(editing) && key === "instrument_code"}
                      title={editing && key === "instrument_code" ? "The instrument code cannot be changed" : undefined}
                      {...register(key, { required })}
                      className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring read-only:cursor-not-allowed read-only:bg-muted read-only:text-muted-foreground"
                    />
                  </div>
                ))}
                {editing && (
                  <div>
                    <label className="text-sm font-medium">Status</label>
                    <select
                      {...register("status")}
                      className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                    >
                      <option value="ACTIVE">ACTIVE</option>
                      <option value="INACTIVE">INACTIVE (retired; no new sessions)</option>
                    </select>
                  </div>
                )}
                {submitError && <p className="text-xs text-status-fail sm:col-span-2">{submitError}</p>}
                <div className="mt-2 sm:col-span-2">
                  <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? "Saving…" : editing ? "Save changes" : "Save instrument"}
                  </Button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
