import React from "react";
import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { StatusBadge } from "@/components/ui/StatusBadge";

// Sample data shaped like it will eventually come from the backend's
// /api/test-sessions endpoints — swap for real fetches once wired up.
const KPIS = [
  { label: "Total test sessions", value: 128 },
  { label: "Pass rate", value: 91, suffix: "%" },
  { label: "Pending review", value: 6 },
  { label: "Reports this month", value: 14 },
];

const RESULT_BREAKDOWN = [
  { name: "Pass", value: 104, color: "hsl(var(--status-pass))" },
  { name: "Fail", value: 9, color: "hsl(var(--status-fail))" },
  { name: "N/A", value: 15, color: "hsl(var(--status-na))" },
];

const MONTHLY_TESTS = [
  { month: "Apr", tests: 14 },
  { month: "May", tests: 18 },
  { month: "Jun", tests: 21 },
  { month: "Jul", tests: 17 },
  { month: "Aug", tests: 26 },
  { month: "Sep", tests: 32 },
];

const RECENT_SESSIONS = [
  { id: "TS-2026-0142", instrument: "Avery Berkel L223 — Platform Scale", tester: "R. Nair", status: "pass", date: "24 Sep 2026" },
  { id: "TS-2026-0141", instrument: "Mettler Toledo IND560 — Bench Scale", tester: "S. Kulkarni", status: "pending", date: "23 Sep 2026" },
  { id: "TS-2026-0140", instrument: "Essae DS-415 — Weighbridge", tester: "A. Verma", status: "fail", date: "22 Sep 2026" },
  { id: "TS-2026-0139", instrument: "Avery Berkel L223 — Platform Scale", tester: "R. Nair", status: "pass", date: "20 Sep 2026" },
];

const PENDING_APPROVALS = [
  { id: "TS-2026-0141", instrument: "Mettler Toledo IND560", submittedBy: "S. Kulkarni" },
  { id: "TS-2026-0138", instrument: "Essae DS-415", submittedBy: "A. Verma" },
];

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Testing activity across your laboratory.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {KPIS.map((kpi, i) => (
          <motion.div
            key={kpi.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05, duration: 0.35 }}
          >
            <Card>
              <CardContent className="pt-5">
                <p className="text-xs font-medium text-muted-foreground">{kpi.label}</p>
                <p className="mt-1 text-3xl font-semibold">
                  <AnimatedNumber value={kpi.value} suffix={kpi.suffix || ""} />
                </p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Tests by month</CardTitle>
          </CardHeader>
          <CardContent className="h-64 pt-0">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={MONTHLY_TESTS}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                <YAxis tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                <Tooltip
                  contentStyle={{
                    borderRadius: 12,
                    border: "1px solid hsl(var(--border))",
                    fontSize: 12,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="tests"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2.5}
                  dot={{ r: 3 }}
                  isAnimationActive
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Result breakdown</CardTitle>
          </CardHeader>
          <CardContent className="h-64 pt-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={RESULT_BREAKDOWN}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={3}
                  isAnimationActive
                >
                  {RESULT_BREAKDOWN.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 12, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="-mt-4 flex justify-center gap-4 text-xs text-muted-foreground">
              {RESULT_BREAKDOWN.map((r) => (
                <span key={r.name} className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full" style={{ background: r.color }} />
                  {r.name}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent test sessions</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="pb-2 font-medium">Session</th>
                  <th className="pb-2 font-medium">Instrument</th>
                  <th className="pb-2 font-medium">Tester</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {RECENT_SESSIONS.map((s, i) => (
                  <motion.tr
                    key={s.id}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="border-t border-border"
                  >
                    <td className="py-2.5 font-num text-xs">{s.id}</td>
                    <td className="py-2.5">{s.instrument}</td>
                    <td className="py-2.5 text-muted-foreground">{s.tester}</td>
                    <td className="py-2.5">
                      <StatusBadge status={s.status} />
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Awaiting your approval</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            {PENDING_APPROVALS.map((a) => (
              <div key={a.id} className="rounded-lg border border-border p-3">
                <p className="font-num text-xs text-muted-foreground">{a.id}</p>
                <p className="text-sm font-medium">{a.instrument}</p>
                <p className="text-xs text-muted-foreground">Submitted by {a.submittedBy}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
