import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useForm } from "react-hook-form";
import { Search, Plus, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
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

export default function Instruments() {
  const { token } = useAuth();
  const [instruments, setInstruments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [query, setQuery] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [submitError, setSubmitError] = useState("");
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

  async function onSubmit(values) {
    setSubmitError("");
    // Cast the number fields (native inputs give strings); drop empties.
    const payload = Object.fromEntries(
      Object.entries(values)
        .filter(([, v]) => v !== "")
        .map(([k, v]) => {
          const field = NEW_INSTRUMENT_FIELDS.find(([key]) => key === k);
          return [k, field?.[3] === "number" ? Number(v) : v];
        })
    );
    try {
      await api.createInstrument(payload, token);
      reset();
      setShowForm(false);
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
        <Button onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4" /> Register instrument
        </Button>
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
                  <th className="pb-2 font-medium">Manufacturer</th>
                  <th className="pb-2 font-medium">Model</th>
                  <th className="pb-2 font-medium">Type</th>
                  <th className="pb-2 font-medium">Accuracy class</th>
                  <th className="pb-2 font-medium">Max / Min / e</th>
                  <th className="pb-2 font-medium">Status</th>
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
                    <td className="py-2.5 font-medium">{inst.manufacturer || "—"}</td>
                    <td className="py-2.5">{inst.model || "—"}</td>
                    <td className="py-2.5 text-muted-foreground">{inst.instrument_type || "—"}</td>
                    <td className="py-2.5 font-num">{inst.accuracy_class || "—"}</td>
                    <td className="py-2.5 font-num text-xs text-muted-foreground">
                      {inst.max_capacity ?? "—"} / {inst.min_capacity ?? "—"} / {inst.verification_scale_interval ?? "—"}
                    </td>
                    <td className="py-2.5">
                      <span className="rounded-full bg-status-pass/10 px-2 py-0.5 text-xs font-medium text-status-pass">
                        {inst.status || "active"}
                      </span>
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
            onClick={() => setShowForm(false)}
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
                <h2 className="font-heading text-lg font-semibold">Register instrument</h2>
                <button onClick={() => setShowForm(false)} data-cursor-hover>
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
                      {...register(key, { required })}
                      className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                ))}
                {submitError && <p className="text-xs text-status-fail sm:col-span-2">{submitError}</p>}
                <div className="mt-2 sm:col-span-2">
                  <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? "Saving…" : "Save instrument"}
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
