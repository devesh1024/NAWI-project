import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useForm } from "react-hook-form";
import { Plus, X, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { RowActions } from "@/components/ui/RowActions";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/apiClient";

const STATUS_LABELS = {
  DRAFT: "Draft",
  "IN PROGRESS": "In progress",
  SUBMITTED: "Submitted",
  "UNDER REVIEW": "Under review",
  APPROVED: "Approved",
  REJECTED: "Rejected",
};

// Mirrors backend/app/services/crud_rules.py. The backend is authoritative;
// this only greys out buttons that would be refused anyway.
const normStatus = (s) => (s || "DRAFT").trim().toUpperCase().replace(/[ -]/g, "_");
const EDITABLE_STATUSES = ["DRAFT", "IN_PROGRESS"];
const DELETABLE_STATUSES = ["DRAFT", "IN_PROGRESS", "REJECTED", "CANCELLED"];

const EMPTY_VALUES = {
  instrument_id: "",
  standard_id: "",
  session_number: "",
  application_number: "",
  remarks: "",
};

function resultBadge(overallResult) {
  if (overallResult === "PASS") return "pass";
  if (overallResult === "FAIL") return "fail";
  return "pending";
}

export default function TestSessions() {
  const { token } = useAuth();
  const [editing, setEditing] = useState(null); // session being edited, null = creating
  const [actionError, setActionError] = useState("");
  const [sessions, setSessions] = useState([]);
  const [instruments, setInstruments] = useState([]);
  const [standards, setStandards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm();

  async function load() {
    setLoading(true);
    setLoadError("");
    try {
      const [s, inst, std] = await Promise.all([
        api.getTestSessions(token),
        api.getInstruments(token),
        api.getStandards(token),
      ]);
      setSessions(s);
      setInstruments(inst);
      setStandards(std);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) load();
  }, [token]);

  function openCreate() {
    setEditing(null);
    setSubmitError("");
    reset(EMPTY_VALUES);
    setShowForm(true);
  }

  function openEdit(s) {
    setEditing(s);
    setSubmitError("");
    reset({
      instrument_id: s.instrument_id,
      standard_id: s.standard_id,
      session_number: s.session_number ?? "",
      application_number: s.application_number ?? "",
      remarks: s.remarks ?? "",
    });
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditing(null);
  }

  async function onSubmit(values) {
    setSubmitError("");
    try {
      if (editing) {
        // A cleared text field is sent as null so it is really cleared.
        const payload = {
          instrument_id: values.instrument_id,
          standard_id: values.standard_id,
          session_number: values.session_number || null,
          application_number: values.application_number || null,
          remarks: values.remarks || null,
        };
        await api.updateTestSession(editing.test_session_id, payload, token);
      } else {
        const payload = Object.fromEntries(Object.entries(values).filter(([, v]) => v !== ""));
        await api.createTestSession(payload, token);
      }
      reset(EMPTY_VALUES);
      closeForm();
      load();
    } catch (err) {
      setSubmitError(err.message);
    }
  }

  async function handleDelete(s) {
    const label = s.session_number || s.test_session_id.slice(0, 8);
    if (!window.confirm(
      `Delete test session ${label}?\n\nAll its tests, observations, results and any draft report are deleted with it. This cannot be undone.`
    )) return;
    setActionError("");
    try {
      await api.deleteTestSession(s.test_session_id, token);
      load();
    } catch (err) {
      setActionError(err.message);
    }
  }

  // Retired (INACTIVE) instruments cannot start new sessions; keep the current one when editing.
  const selectableInstruments = instruments.filter(
    (i) => (i.status || "").toUpperCase() !== "INACTIVE" || i.instrument_id === editing?.instrument_id
  );

  function instrumentLabel(id) {
    const i = instruments.find((i) => i.instrument_id === id);
    return i ? `${i.manufacturer || ""} ${i.model || ""}`.trim() || i.instrument_code : id;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Test Sessions</h1>
          <p className="text-sm text-muted-foreground">Every OIML R-76 test run against an instrument.</p>
        </div>
        <Button onClick={openCreate} disabled={instruments.length === 0 || standards.length === 0}>
          <Plus className="h-4 w-4" /> New test session
        </Button>
      </div>

      {(instruments.length === 0 || standards.length === 0) && !loading && (
        <p className="rounded-lg bg-muted px-3 py-2 text-xs text-muted-foreground">
          {instruments.length === 0 && "Register an instrument first. "}
          {standards.length === 0 && "No standards exist yet — add one under Standards & Rules first."}
        </p>
      )}

      {actionError && (
        <p className="rounded-lg bg-status-fail/10 px-3 py-2 text-sm text-status-fail">{actionError}</p>
      )}

      <Card>
        <CardContent className="pt-5">
          {loading && <p className="py-6 text-center text-sm text-muted-foreground">Loading sessions…</p>}
          {loadError && <p className="py-6 text-center text-sm text-status-fail">{loadError}</p>}
          {!loading && !loadError && sessions.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">No test sessions yet.</p>
          )}
          {!loading && !loadError && sessions.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="pb-2 font-medium">Session</th>
                  <th className="pb-2 font-medium">Instrument</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Result</th>
                  <th className="pb-2 font-medium" />
                  <th className="pb-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {sessions.map((s, i) => (
                  <motion.tr
                    key={s.test_session_id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="border-t border-border"
                  >
                    <td className="py-2.5 font-num text-xs">{s.session_number || s.test_session_id.slice(0, 8)}</td>
                    <td className="py-2.5">{instrumentLabel(s.instrument_id)}</td>
                    <td className="py-2.5 text-muted-foreground">{STATUS_LABELS[s.status] || s.status}</td>
                    <td className="py-2.5">
                      {s.overall_result ? <StatusBadge status={resultBadge(s.overall_result)} /> : <span className="text-xs text-muted-foreground">—</span>}
                    </td>
                    <td className="py-2.5 text-right">
                      <Link
                        to={`/app/test-sessions/${s.test_session_id}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                        data-cursor-hover
                      >
                        Open <ChevronRight className="h-3.5 w-3.5" />
                      </Link>
                    </td>
                    <td className="py-2.5">
                      <RowActions
                        onEdit={() => openEdit(s)}
                        editDisabled={
                          !EDITABLE_STATUSES.includes(normStatus(s.status)) &&
                          "Only Draft or In-progress sessions can be edited"
                        }
                        onDelete={() => handleDelete(s)}
                        deleteDisabled={
                          !DELETABLE_STATUSES.includes(normStatus(s.status)) &&
                          "Submitted, approved or under-review sessions cannot be deleted"
                        }
                      />
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
              className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-raised"
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-heading text-lg font-semibold">
                  {editing ? "Edit test session" : "New test session"}
                </h2>
                <button type="button" onClick={closeForm} data-cursor-hover>
                  <X className="h-5 w-5 text-muted-foreground" />
                </button>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
                <div>
                  <label className="text-sm font-medium">Instrument</label>
                  <select {...register("instrument_id", { required: true })} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring">
                    <option value="">Select instrument…</option>
                    {selectableInstruments.map((i) => (
                      <option key={i.instrument_id} value={i.instrument_id}>
                        {i.manufacturer} {i.model} ({i.instrument_code})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Standard</label>
                  <select {...register("standard_id", { required: true })} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring">
                    <option value="">Select standard…</option>
                    {standards.map((s) => (
                      <option key={s.standard_id} value={s.standard_id}>{s.standard_code} — {s.title}</option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium">Session number</label>
                    <input placeholder="TS-2026-001" {...register("session_number")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Application no.</label>
                    <input placeholder="APP-2026-001" {...register("application_number")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                  </div>
                </div>
                {editing && (
                  <div>
                    <label className="text-sm font-medium">Remarks</label>
                    <textarea
                      rows={3}
                      {...register("remarks")}
                      className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                    />
                    <p className="mt-1 text-xs text-muted-foreground">
                      The instrument and standard can only be changed before any test has been added.
                    </p>
                  </div>
                )}
                {submitError && <p className="text-xs text-status-fail">{submitError}</p>}
                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? (editing ? "Saving…" : "Creating…") : editing ? "Save changes" : "Create session"}
                </Button>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
