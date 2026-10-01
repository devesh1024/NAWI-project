import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/Card";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/apiClient";

export default function AuditLog() {
  const { token } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api.getAuditLogs(token)
      .then(setLogs)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Audit Log</h1>
        <p className="text-sm text-muted-foreground">Activity recorded for your laboratory, latest first.</p>
      </div>

      <Card>
        <CardContent className="pt-5">
          {loading && <p className="py-6 text-center text-sm text-muted-foreground">Loading…</p>}
          {error && <p className="py-6 text-center text-sm text-status-fail">{error}</p>}
          {!loading && !error && logs.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">No activity recorded yet.</p>
          )}
          {!loading && !error && logs.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="pb-2 font-medium">Time</th>
                  <th className="pb-2 font-medium">Action</th>
                  <th className="pb-2 font-medium">Entity</th>
                  <th className="pb-2 font-medium">Remarks</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l, i) => (
                  <motion.tr
                    key={l.audit_id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(i * 0.03, 0.3) }}
                    className="border-t border-border"
                  >
                    <td className="py-2.5 font-num text-xs text-muted-foreground">
                      {l.timestamp ? new Date(l.timestamp).toLocaleString() : "—"}
                    </td>
                    <td className="py-2.5">
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                        {l.action}
                      </span>
                    </td>
                    <td className="py-2.5 font-num text-xs text-muted-foreground">
                      {l.entity_type} {l.entity_id ? `#${String(l.entity_id).slice(0, 8)}` : ""}
                    </td>
                    <td className="py-2.5 text-muted-foreground">{l.remarks || "—"}</td>
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
