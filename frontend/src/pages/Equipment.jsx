import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useForm } from "react-hook-form";
import { Plus, X, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/apiClient";

const CALIBRATION_STATUS_STYLES = {
  VALID: "bg-status-pass/10 text-status-pass",
  DUE_SOON: "bg-status-pending/10 text-status-pending",
  OVERDUE: "bg-status-fail/10 text-status-fail",
};

export default function Equipment() {
  const { token } = useAuth();
  const [equipment, setEquipment] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm();

  async function load() {
    setLoading(true);
    setLoadError("");
    try {
      setEquipment(await api.getTestEquipment(token));
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) load();
  }, [token]);

  async function onSubmit(values) {
    setSubmitError("");
    try {
      const payload = Object.fromEntries(
        Object.entries(values).filter(([, v]) => v !== "")
      );
      await api.createTestEquipment(payload, token);
      reset();
      setShowForm(false);
      load();
    } catch (err) {
      setSubmitError(err.message);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this equipment record?")) return;
    try {
      await api.deleteTestEquipment(id, token);
      load();
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Equipment</h1>
          <p className="text-sm text-muted-foreground">Lab test equipment and calibration status.</p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4" /> Add equipment
        </Button>
      </div>

      {/* TODO: assigning equipment to a specific test session test
          (POST /api/test-equipment/{id}/assign, per her router) isn't wired
          to any UI yet — the natural place is from within a test session's
          test row, once that flow exists. The endpoint is ready. */}

      <Card>
        <CardContent className="pt-5">
          {loading && <p className="py-6 text-center text-sm text-muted-foreground">Loading equipment…</p>}
          {loadError && <p className="py-6 text-center text-sm text-status-fail">{loadError}</p>}
          {!loading && !loadError && equipment.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">No equipment registered yet.</p>
          )}
          {!loading && !loadError && equipment.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="pb-2 font-medium">Name</th>
                  <th className="pb-2 font-medium">Model / Serial</th>
                  <th className="pb-2 font-medium">Calibration status</th>
                  <th className="pb-2 font-medium">Calibration due</th>
                  <th className="pb-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {equipment.map((eq, i) => (
                  <motion.tr
                    key={eq.equipment_id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="border-t border-border"
                  >
                    <td className="py-2.5 font-medium">{eq.equipment_name}</td>
                    <td className="py-2.5 font-num text-xs text-muted-foreground">
                      {eq.model || "—"} / {eq.serial_number || "—"}
                    </td>
                    <td className="py-2.5">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${CALIBRATION_STATUS_STYLES[eq.calibration_status] || "bg-muted text-muted-foreground"}`}>
                        {eq.calibration_status || "UNKNOWN"}
                      </span>
                    </td>
                    <td className="py-2.5 font-num text-xs text-muted-foreground">
                      {eq.calibration_due_date ? new Date(eq.calibration_due_date).toLocaleDateString() : "—"}
                    </td>
                    <td className="py-2.5 text-right">
                      <button onClick={() => handleDelete(eq.equipment_id)} data-cursor-hover>
                        <Trash2 className="h-4 w-4 text-muted-foreground hover:text-status-fail" />
                      </button>
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
              className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-raised"
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-heading text-lg font-semibold">Add equipment</h2>
                <button onClick={() => setShowForm(false)} data-cursor-hover>
                  <X className="h-5 w-5 text-muted-foreground" />
                </button>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
                <div>
                  <label className="text-sm font-medium">Equipment name</label>
                  <input {...register("equipment_name", { required: true })} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium">Model</label>
                    <input {...register("model")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Serial number</label>
                    <input {...register("serial_number")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium">Calibration status</label>
                  <select {...register("calibration_status")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring">
                    <option value="">—</option>
                    <option value="VALID">Valid</option>
                    <option value="DUE_SOON">Due soon</option>
                    <option value="OVERDUE">Overdue</option>
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium">Calibration date</label>
                    <input type="date" {...register("calibration_date")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Due date</label>
                    <input type="date" {...register("calibration_due_date")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                  </div>
                </div>
                {submitError && <p className="text-xs text-status-fail">{submitError}</p>}
                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? "Saving…" : "Save equipment"}
                </Button>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
