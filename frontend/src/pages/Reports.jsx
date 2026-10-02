import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { FileDown, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { RowActions } from "@/components/ui/RowActions";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useAuth } from "@/hooks/useAuth";
import { api, downloadResponse } from "@/lib/apiClient";

// Lists real report records from GET /api/reports (one row per generated report).
// Generating and approving a report still happen on the test session page.

function resultBadge(overallResult) {
  if (overallResult === "PASS") return "pass";
  if (overallResult === "FAIL") return "fail";
  return "pending";
}

const isApproved = (report) => (report.report_status || "").toUpperCase() === "APPROVED";

export default function Reports() {
  const { token, role } = useAuth();
  const isAdmin = role === "LAB_ADMIN";

  const [reports, setReports] = useState([]);
  const [instruments, setInstruments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");

  const [editing, setEditing] = useState(null); // report whose remarks are being edited
  const [remarks, setRemarks] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  async function load() {
    setLoading(true);
    setLoadError("");
    try {
      const [r, inst] = await Promise.all([api.getReports(token), api.getInstruments(token)]);
      setReports(r);
      setInstruments(inst);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) load();
  }, [token]);

  function instrumentLabel(id) {
    const i = instruments.find((i) => i.instrument_id === id);
    return i ? `${i.manufacturer || ""} ${i.model || ""}`.trim() || i.instrument_code : "—";
  }

  async function handleDownload(report, type) {
    setActionError("");
    try {
      const res =
        type === "pdf"
          ? await api.downloadPdf(report.test_session_id, token)
          : await api.downloadDocx(report.test_session_id, token);
      await downloadResponse(res, `${report.report_number || "NAWI_Report"}.${type}`);
    } catch (err) {
      setActionError(`${report.report_number || "Report"}: ${err.message}`);
    }
  }

  function openEdit(report) {
    setEditing(report);
    setRemarks(report.remarks ?? "");
    setSaveError("");
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setSaveError("");
    try {
      await api.updateReport(editing.report_id, { remarks: remarks || null }, token);
      setEditing(null);
      load();
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(report) {
    if (!window.confirm(
      `Delete report ${report.report_number || ""}?\n\nThe generated PDF/DOCX files are removed too. ` +
      `You can generate a new report from the test session afterwards.`
    )) return;
    setActionError("");
    try {
      await api.deleteReport(report.report_id, token);
      load();
    } catch (err) {
      setActionError(err.message);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Reports</h1>
        <p className="text-sm text-muted-foreground">Generated test reports. Generate or approve a report from its test session.</p>
      </div>

      {actionError && <p className="rounded-lg bg-status-fail/10 px-3 py-2 text-xs text-status-fail">{actionError}</p>}

      <Card>
        <CardContent className="pt-5">
          {loading && <p className="py-6 text-center text-sm text-muted-foreground">Loading…</p>}
          {loadError && <p className="py-6 text-center text-sm text-status-fail">{loadError}</p>}
          {!loading && !loadError && reports.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No reports yet. Open a test session and use "Generate report".
            </p>
          )}
          {!loading && !loadError && reports.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="pb-2 font-medium">Report</th>
                  <th className="pb-2 font-medium">Session</th>
                  <th className="pb-2 font-medium">Instrument</th>
                  <th className="pb-2 font-medium">Result</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Remarks</th>
                  <th className="pb-2 font-medium" />
                  <th className="pb-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {reports.map((r, i) => (
                  <motion.tr
                    key={r.report_id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="border-t border-border"
                  >
                    <td className="py-2.5 font-num text-xs">
                      {r.report_number}
                      {r.report_version ? <span className="text-muted-foreground"> v{r.report_version}</span> : null}
                    </td>
                    <td className="py-2.5 font-num text-xs">{r.session_number || r.test_session_id.slice(0, 8)}</td>
                    <td className="py-2.5">{instrumentLabel(r.instrument_id)}</td>
                    <td className="py-2.5">
                      {r.overall_result ? <StatusBadge status={resultBadge(r.overall_result)} /> : "—"}
                    </td>
                    <td className="py-2.5 text-muted-foreground">{r.report_status || "—"}</td>
                    <td className="max-w-[14rem] truncate py-2.5 text-xs text-muted-foreground" title={r.remarks || ""}>
                      {r.remarks || "—"}
                    </td>
                    <td className="py-2.5">
                      <div className="flex items-center justify-end gap-3">
                        <button onClick={() => handleDownload(r, "pdf")} className="text-xs font-medium text-primary hover:underline" data-cursor-hover>
                          <FileDown className="mr-1 inline h-3.5 w-3.5" />PDF
                        </button>
                        <button onClick={() => handleDownload(r, "docx")} className="text-xs font-medium text-primary hover:underline" data-cursor-hover>
                          <FileDown className="mr-1 inline h-3.5 w-3.5" />DOCX
                        </button>
                        <Link to={`/app/test-sessions/${r.test_session_id}`} className="inline-flex items-center text-xs text-muted-foreground hover:text-foreground" data-cursor-hover>
                          Open <ChevronRight className="h-3.5 w-3.5" />
                        </Link>
                      </div>
                    </td>
                    <td className="py-2.5">
                      <RowActions
                        onEdit={() => openEdit(r)}
                        editDisabled={isApproved(r) && "Approved reports cannot be edited"}
                        onDelete={isAdmin ? () => handleDelete(r) : null}
                        deleteDisabled={isApproved(r) && "Approved reports are permanent records"}
                      />
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <Modal
        open={Boolean(editing)}
        title={`Edit report ${editing?.report_number || ""}`}
        onClose={() => setEditing(null)}
        maxWidth="max-w-md"
      >
        <form onSubmit={handleSave} className="space-y-3">
          <div>
            <label className="text-sm font-medium">Remarks</label>
            <textarea
              rows={4}
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Only remarks can be edited. The result and content come from the test session; regenerate the report to refresh them.
            </p>
          </div>
          {saveError && <p className="text-xs text-status-fail">{saveError}</p>}
          <Button type="submit" className="w-full" disabled={saving}>
            {saving ? "Saving…" : "Save changes"}
          </Button>
        </form>
      </Modal>
    </div>
  );
}
