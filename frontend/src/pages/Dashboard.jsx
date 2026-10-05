import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import { ArrowUpRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { SessionStatus } from "@/components/ui/SessionStatus";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/apiClient";
import { roleTone } from "@/lib/roles";
import { cn } from "@/lib/utils";

const RESULT_COLORS = {
  PASS: "hsl(var(--status-pass))",
  FAIL: "hsl(var(--status-fail))",
  "N/A": "hsl(var(--status-na))",
};

// How a KPI's tone changes its card: a coloured edge, never a coloured fill.
const KPI_EDGE = {
  default: "border-l-transparent",
  good: "border-l-status-pass",
  warn: "border-l-status-pending",
  bad: "border-l-status-fail",
};

const tooltipStyle = { borderRadius: 12, border: "1px solid hsl(var(--border))", fontSize: 12 };

function timeAgo(iso) {
  if (!iso) return "";
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  if (mins < 1440) return `${Math.round(mins / 60)} h ago`;
  return new Date(iso).toLocaleDateString([], { day: "2-digit", month: "short" });
}

function Kpi({ kpi, index }) {
  const body = (
    <Card className={cn("border-l-4", KPI_EDGE[kpi.tone] || KPI_EDGE.default, kpi.href && "transition hover:shadow-raised")}>
      <CardContent className="pt-5">
        <p className="text-xs font-medium text-muted-foreground">{kpi.label}</p>
        <p className="mt-1 text-3xl font-semibold">
          <AnimatedNumber value={Number(kpi.value) || 0} suffix={kpi.suffix || ""} />
        </p>
      </CardContent>
    </Card>
  );

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05, duration: 0.35 }}>
      {kpi.href ? (
        <Link to={kpi.href} data-cursor-hover className="block">{body}</Link>
      ) : body}
    </motion.div>
  );
}

function Queue({ queue }) {
  const { title, items, empty, total, href } = queue;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>
          {title}
          {total > 0 && <span className="font-num ml-2 text-sm font-normal text-muted-foreground">{total}</span>}
        </CardTitle>
        {href && (
          <Link to={href} className="flex items-center gap-1 text-xs font-medium text-primary hover:underline" data-cursor-hover>
            Open <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        )}
      </CardHeader>
      <CardContent className="pt-0">
        {items.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground">{empty}</p>
        ) : (
          <ul className="divide-y divide-border">
            {items.map((item) => (
              <li key={item.id}>
                <Link
                  to={item.href}
                  className="-mx-2 flex items-center justify-between gap-3 rounded-lg px-2 py-2.5 hover:bg-muted"
                  data-cursor-hover
                >
                  <span className="min-w-0">
                    <span className="font-num block truncate text-xs text-muted-foreground">{item.title}</span>
                    <span className="block truncate text-sm font-medium">{item.subtitle}</span>
                    {(item.meta || item.note) && (
                      <span className="block truncate text-xs text-muted-foreground">
                        {[item.meta, item.note].filter(Boolean).join(" · ")}
                      </span>
                    )}
                  </span>
                  <span className="flex shrink-0 flex-col items-end gap-1">
                    <SessionStatus status={item.badge} />
                    {item.result && (
                      <span className={cn("font-num text-[11px] font-semibold", item.result === "PASS" ? "text-status-pass" : "text-status-fail")}>
                        {item.result}
                      </span>
                    )}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function Charts({ charts }) {
  const results = (charts.results || []).filter((r) => r.value > 0);
  const hasResults = results.length > 0;

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {charts.monthly && (
        <Card className={charts.pipeline || charts.results ? "lg:col-span-2" : "lg:col-span-3"}>
          <CardHeader><CardTitle>Test sessions by month</CardTitle></CardHeader>
          <CardContent className="h-64 pt-0">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={charts.monthly}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="tests" name="Sessions" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={{ r: 3 }} isAnimationActive />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {charts.results && (
        <Card className={!charts.monthly ? "lg:col-span-1" : undefined}>
          <CardHeader><CardTitle>Test results</CardTitle></CardHeader>
          <CardContent className="h-64 pt-0">
            {hasResults ? (
              <>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={results} dataKey="value" nameKey="name" innerRadius={55} outerRadius={80} paddingAngle={3} isAnimationActive>
                      {results.map((r) => <Cell key={r.name} fill={RESULT_COLORS[r.name]} />)}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="-mt-4 flex justify-center gap-4 text-xs text-muted-foreground">
                  {results.map((r) => (
                    <span key={r.name} className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full" style={{ background: RESULT_COLORS[r.name] }} />
                      {r.name} <span className="font-num">{r.value}</span>
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <p className="flex h-full items-center justify-center text-sm text-muted-foreground">No results recorded yet.</p>
            )}
          </CardContent>
        </Card>
      )}

      {charts.pipeline && (
        <Card className={charts.monthly ? "lg:col-span-3" : "lg:col-span-2"}>
          <CardHeader><CardTitle>Where the work is</CardTitle></CardHeader>
          <CardContent className="h-56 pt-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={charts.pipeline} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                <YAxis type="category" dataKey="status" width={96} tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(var(--muted))" }} />
                <Bar dataKey="count" name="Sessions" fill="hsl(var(--primary))" radius={[0, 6, 6, 0]} isAnimationActive />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Activity({ items, title }) {
  if (!items?.length) return null;
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="pt-0">
        <ul className="divide-y divide-border">
          {items.map((a, i) => (
            <li key={i} className="flex items-start justify-between gap-4 py-2.5 text-sm">
              <span className="min-w-0">
                <span className="font-num text-xs font-semibold">{a.action.replace(/_/g, " ")}</span>{" "}
                <span className="text-muted-foreground">{a.entity_type?.replace(/_/g, " ").toLowerCase()}</span>
                <span className="block truncate text-xs text-muted-foreground">
                  {[a.by, a.by_role].filter(Boolean).join(" · ")}
                  {a.remarks ? ` · ${a.remarks}` : ""}
                </span>
              </span>
              <span className="shrink-0 text-xs text-muted-foreground">{timeAgo(a.at)}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { token, role, roleLabel, name } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    api.getDashboard(token)
      .then((d) => live && setData(d))
      .catch((e) => live && setError(e.message));
    return () => { live = false; };
  }, [token, role]);

  if (error) return <p className="text-sm text-status-fail">Could not load your dashboard: {error}</p>;
  if (!data) return <p className="text-sm text-muted-foreground">Loading your dashboard…</p>;

  const first = (name || "").split(" ")[0];
  const queues = data.queues || [];
  const wide = queues.length === 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{data.headline}</h1>
          <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">{data.hint}</p>
        </div>
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          {first && <span>Signed in as {first}</span>}
          <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium", roleTone(role))}>{roleLabel}</span>
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-[repeat(auto-fit,minmax(180px,1fr))]">
        {data.kpis.map((kpi, i) => <Kpi key={kpi.key} kpi={kpi} index={i} />)}
      </div>

      <div className={cn("grid gap-4", wide ? "" : "lg:grid-cols-2")}>
        {queues.map((q) => <Queue key={q.key} queue={q} />)}
      </div>

      {data.charts && <Charts charts={data.charts} />}

      <Activity items={data.activity} title="Recent activity" />
    </div>
  );
}
