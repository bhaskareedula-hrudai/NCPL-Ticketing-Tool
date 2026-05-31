import React from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/hooks/useAsync";
import { CircleNotch } from "@phosphor-icons/react";
import { STATUS_CHART_COLORS, PRIORITY_CHART_COLORS, DEPT_COLORS } from "@/lib/constants";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
  PieChart, Pie, Legend, AreaChart, Area,
} from "recharts";

const TICK       = { fontSize: 11, fill: "#595959" };
const TICK_LIGHT = { fontSize: 11, fill: "#8C8C8C" };
const TOOLTIP_STYLE  = { background: "#fff", border: "1px solid #E5E2DC", borderRadius: 6, fontSize: 12 };

export default function Reports() {
  const { data: stats, loading } = useAsync(
    () => api.get("/dashboard/stats").then((r) => r.data),
    [],
  );

  if (loading) {
    return <div className="p-8 flex items-center gap-2 mono-label"><CircleNotch className="animate-spin" /> Loading reports…</div>;
  }

  return (
    <div className="p-6 md:p-8 max-w-[1500px]" data-testid="reports-page">
      <div className="mb-6">
        <div className="mono-label">Analytics</div>
        <h1 className="text-3xl font-semibold mt-1" style={{ fontFamily: "Cabinet Grotesk" }}>Reports</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          Operational insights across departments, statuses and priorities.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Metric label="Total"    value={stats.total}    testid="report-metric-total" />
        <Metric label="Active"   value={stats.active}   testid="report-metric-active" />
        <Metric label="Resolved" value={stats.resolved} testid="report-metric-resolved" />
        <Metric label="Closed"   value={stats.closed}   testid="report-metric-closed" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Tickets by Department">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats.by_department}>
              <CartesianGrid strokeDasharray="2 4" stroke="#E5E2DC" vertical={false} />
              <XAxis dataKey="department" tick={TICK} axisLine={false} tickLine={false} />
              <YAxis tick={TICK_LIGHT} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {stats.by_department.map((e, i) => <Cell key={e.department} fill={DEPT_COLORS[i % DEPT_COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Status Distribution">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={stats.by_status} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={90} innerRadius={50} paddingAngle={2}>
                {stats.by_status.map((e) => <Cell key={e.status} fill={STATUS_CHART_COLORS[e.status] || "#3A4B59"} />)}
              </Pie>
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend iconType="square" wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Priority Mix">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats.by_priority} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="2 4" stroke="#E5E2DC" horizontal={false} />
              <XAxis type="number" tick={TICK_LIGHT} axisLine={false} tickLine={false} allowDecimals={false} />
              <YAxis dataKey="priority" type="category" tick={TICK} axisLine={false} tickLine={false} width={70} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {stats.by_priority.map((e) => <Cell key={e.priority} fill={PRIORITY_CHART_COLORS[e.priority] || "#3A4B59"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Trend · Last 7 Days">
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={stats.trend_7d}>
              <defs>
                <linearGradient id="gradTrend" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#3A4B59" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#3A4B59" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" stroke="#E5E2DC" vertical={false} />
              <XAxis dataKey="date" tick={TICK_LIGHT} axisLine={false} tickLine={false} />
              <YAxis tick={TICK_LIGHT} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Area type="monotone" dataKey="count" stroke="#3A4B59" strokeWidth={2} fill="url(#gradTrend)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}

function Metric({ label, value, testid }) {
  return (
    <div className="stat-card" data-testid={testid}>
      <div className="mono-label">{label}</div>
      <div className="mt-2 text-3xl font-semibold" style={{ fontFamily: "Cabinet Grotesk", letterSpacing: "-0.02em" }}>{value}</div>
    </div>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="card-flat p-5">
      <div className="mono-label">Breakdown</div>
      <h3 className="text-lg font-medium mt-1 mb-4" style={{ fontFamily: "Cabinet Grotesk" }}>{title}</h3>
      {children}
    </div>
  );
}
