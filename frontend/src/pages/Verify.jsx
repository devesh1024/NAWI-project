import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Upload, ShieldCheck, ShieldAlert, ShieldQuestion, QrCode } from "lucide-react";
import { MarketingNav } from "@/components/layout/MarketingNav";
import { Card, CardContent } from "@/components/ui/Card";
import { api } from "@/lib/apiClient";

// Three distinct trust levels, deliberately not conflated in this UI — see
// backend/app/api/verify/routes.py's docstring for the full reasoning:
//   1. Landed here via QR scan (testSessionId in the URL)  -> DB lookup only, "light" check.
//   2. Uploaded a PDF                                      -> real cryptographic tamper check.
//   3. Uploaded a DOCX                                     -> metadata-only cross-check, caveated.

const VERDICT_STYLES = {
  AUTHENTIC: { icon: ShieldCheck, color: "text-status-pass", bg: "bg-status-pass/10", label: "Authentic" },
  FOUND: { icon: ShieldQuestion, color: "text-status-pending", bg: "bg-status-pending/10", label: "Record found" },
  FOUND_IN_SYSTEM: { icon: ShieldQuestion, color: "text-status-pending", bg: "bg-status-pending/10", label: "Matches a system record" },
  TAMPERED: { icon: ShieldAlert, color: "text-status-fail", bg: "bg-status-fail/10", label: "Modified — do not trust" },
  NOT_FOUND: { icon: ShieldAlert, color: "text-status-fail", bg: "bg-status-fail/10", label: "Not found" },
  UNSIGNED: { icon: ShieldAlert, color: "text-status-pending", bg: "bg-status-pending/10", label: "No signature present" },
  UNTRUSTED_SIGNER: { icon: ShieldAlert, color: "text-status-pending", bg: "bg-status-pending/10", label: "Signer not recognised" },
  UNVERIFIABLE: { icon: ShieldQuestion, color: "text-muted-foreground", bg: "bg-muted", label: "Could not verify" },
};

function ResultCard({ result }) {
  const style = VERDICT_STYLES[result.verdict] || VERDICT_STYLES.UNVERIFIABLE;
  const Icon = style.icon;
  const r = result.record;

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${style.bg} ${style.color}`}>
              <Icon className="h-5 w-5" />
            </span>
            <div>
              <p className={`font-heading text-lg font-semibold ${style.color}`}>{style.label}</p>
              <p className="mt-1 text-sm text-muted-foreground">{result.message}</p>
            </div>
          </div>

          {result.signature && (
            <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-1 rounded-lg bg-muted/50 p-3 text-xs sm:grid-cols-4">
              <span>Signed: <span className="font-num">{String(result.signature.signed)}</span></span>
              <span>Intact: <span className="font-num">{String(result.signature.intact)}</span></span>
              <span>Trusted: <span className="font-num">{String(result.signature.trusted)}</span></span>
              <span>Valid: <span className="font-num">{String(result.signature.valid)}</span></span>
            </div>
          )}

          {(result.signature?.reason || result.signature?.error) && (
            <p className="mt-2 break-words text-xs text-muted-foreground">
              Detail: {result.signature.reason || result.signature.error}
            </p>
          )}

          {r && (
            <div className="mt-4 grid gap-x-6 gap-y-1.5 border-t border-border pt-4 text-sm sm:grid-cols-2">
              <span className="text-muted-foreground">Report No. <span className="font-num text-foreground">{r.report_number || "—"}</span></span>
              <span className="text-muted-foreground">Version <span className="font-num text-foreground">{r.report_version || "—"}</span></span>
              <span className="text-muted-foreground">Laboratory <span className="text-foreground">{r.laboratory_name || "—"}</span></span>
              <span className="text-muted-foreground">Instrument <span className="text-foreground">{r.instrument_manufacturer} {r.instrument_model}</span></span>
              <span className="text-muted-foreground">Result <span className="font-num text-foreground">{r.overall_result || "—"}</span></span>
              <span className="text-muted-foreground">Status <span className="text-foreground">{r.report_status || "—"}</span></span>
              <span className="text-muted-foreground">Generated <span className="font-num text-foreground">{r.generated_at ? new Date(r.generated_at).toLocaleString() : "—"}</span></span>
              {r.approved_at && (
                <span className="text-muted-foreground">Approved <span className="font-num text-foreground">{new Date(r.approved_at).toLocaleString()}</span></span>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default function Verify() {
  const { testSessionId } = useParams();
  const [lightResult, setLightResult] = useState(null);
  const [lightError, setLightError] = useState("");
  const [lightLoading, setLightLoading] = useState(false);

  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    if (!testSessionId) return;
    setLightLoading(true);
    api.verifyReportById(testSessionId)
      .then(setLightResult)
      .catch((err) => setLightError(err.message))
      .finally(() => setLightLoading(false));
  }, [testSessionId]);

  const handleFile = useCallback(async (file) => {
    if (!file) return;
    setUploading(true);
    setUploadError("");
    setUploadResult(null);
    try {
      const result = await api.verifyReportUpload(file);
      setUploadResult(result);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  }, []);

  return (
    <div>
      <MarketingNav />
      <div className="container max-w-2xl py-16">
        <h1 className="text-center text-2xl font-semibold md:text-3xl">Verify a report</h1>
        <p className="mx-auto mt-2 max-w-md text-center text-sm text-muted-foreground">
          Anyone can check whether a TulaSetu report is genuine — no account needed.
        </p>

        {testSessionId && (
          <div className="mt-8">
            <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <QrCode className="h-3.5 w-3.5" /> From QR scan — quick check
            </p>
            {lightLoading && <p className="text-sm text-muted-foreground">Checking…</p>}
            {lightError && <p className="text-sm text-status-fail">{lightError}</p>}
            {lightResult && <ResultCard result={lightResult} />}
          </div>
        )}

        <div className="mt-10">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Full check — upload the file
          </p>
          <p className="mb-3 text-xs text-muted-foreground">
            Uploading the PDF performs a real cryptographic tamper check. Uploading a Word
            document can only confirm it matches a record in our system — Word files cannot
            be checked for tampering. When in doubt, use the PDF.
          </p>
          <label
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleFile(e.dataTransfer.files?.[0]);
            }}
            className={`flex cursor-pointer flex-col items-center gap-2 rounded-2xl border-2 border-dashed p-10 text-center transition-colors ${
              dragOver ? "border-primary bg-primary/5" : "border-border bg-surface"
            }`}
            data-cursor-hover
          >
            <Upload className="h-6 w-6 text-muted-foreground" />
            <span className="text-sm font-medium">Drop a PDF or DOCX here, or click to choose a file</span>
            <input
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
          </label>

          <div className="mt-4 space-y-4">
            {uploading && <p className="text-sm text-muted-foreground">Checking file…</p>}
            {uploadError && <p className="text-sm text-status-fail">{uploadError}</p>}
            {uploadResult && <ResultCard result={uploadResult} />}
          </div>
        </div>
      </div>
    </div>
  );
}
