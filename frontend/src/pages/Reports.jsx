import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { FileDown, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useAuth } from "@/hooks/useAuth";
import { api, downloadResponse } from "@/lib/apiClient";

// NOTE: there is no GET /api/reports "list all reports" endpoint on the
// backend yet — reports are only reachable per test-session (report-data /
// generate-report / download-docx / download-pdf, all scoped by
// test_session_id). So this page works off the test sessions list instead.
// If a dedicated reports list endpoint gets added later, swap the fetch
// below for that — the rest of this page's shape can mostly stay the same.

function resultBadge(overallResult) {
  if (overallResult === "PASS") return "pass";
  if (overallResult === "FAIL") return "fail";
  return "pending";
}

export default function Reports() {
  const { token } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [instruments, setInstruments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [downloadError, setDownloadError] = useState("");

  useEffect(() => {
    if (!token) return;
    (async () => {
      setLoading(true);
      setLoadError("");
      try {
        const [s, inst] = await Promise.all([api.getTestSessions(token), api.getInstruments(token)]);
        // Only sessions that have actually progressed far enough to plausibly
        // have a generated report — adjust this filter once report status
        // is exposed more directly.
        setSessions(s.filter((sess) => ["SUBMITTED", "UNDER REVIEW", "APPROVED", "REJECTED"].includes(sess.status)));
        setInstruments(inst);
      } catch (err) {
        setLoadError(err.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  function instrumentLabel(id) {
    const i = instruments.find((i) => i.instrument_id === id);
    return i ? `${i.manufacturer || ""} ${i.model || ""}`.trim() || i.instrument_code : id;
  }

  async function handleDownload(sessionId, type) {
    setDownloadError("");
    try {
      const res = type === "pdf" ? await api.downloadPdf(sessionId, token) : await api.downloadDocx(sessionId, token);
      await downloadResponse(res, `NAWI_Report_${sessionId}.${type}`);
    } catch (err) {
      setDownloadError(`${sessionId.slice(0, 8)}: ${err.message} (report may not be generated yet)`);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Reports</h1>
        <p className="text-sm text-muted-foreground">Generated test reports, by session.</p>
      </div>

      {downloadError && <p className="rounded-lg bg-status-fail/10 px-3 py-2 text-xs text-status-fail">{downloadError}</p>}

      <Card>
        <CardContent className="pt-5">
          {loading && <p className="py-6 text-center text-sm text-muted-foreground">Loading…</p>}
          {loadError && <p className="py-6 text-center text-sm text-status-fail">{loadError}</p>}
          {!loading && !loadError && sessions.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No submitted sessions yet — reports appear here once a session is submitted.
            </p>
          )}
          {!loading && !loadError && sessions.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="pb-2 font-medium">Session</th>
                  <th className="pb-2 font-medium">Instrument</th>
                  <th className="pb-2 font-medium">Result</th>
                  <th className="pb-2 font-medium">Status</th>
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
                    <td className="py-2.5">
                      {s.overall_result ? <StatusBadge status={resultBadge(s.overall_result)} /> : "—"}
                    </td>
                    <td className="py-2.5 text-muted-foreground">{s.status}</td>
                    <td className="py-2.5">
                      <div className="flex items-center justify-end gap-3">
                        <button onClick={() => handleDownload(s.test_session_id, "pdf")} className="text-xs font-medium text-primary hover:underline" data-cursor-hover>
                          <FileDown className="mr-1 inline h-3.5 w-3.5" />PDF
                        </button>
                        <button onClick={() => handleDownload(s.test_session_id, "docx")} className="text-xs font-medium text-primary hover:underline" data-cursor-hover>
                          <FileDown className="mr-1 inline h-3.5 w-3.5" />DOCX
                        </button>
                        <Link to={`/app/test-sessions/${s.test_session_id}`} className="inline-flex items-center text-xs text-muted-foreground hover:text-foreground" data-cursor-hover>
                          Open <ChevronRight className="h-3.5 w-3.5" />
                        </Link>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
