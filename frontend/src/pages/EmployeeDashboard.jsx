import React from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { useAsync } from "@/hooks/useAsync";
import TicketTable from "@/components/common/TicketTable";
import { ArrowUpRight, CircleNotch, Plus } from "@phosphor-icons/react";
import { greeting } from "@/lib/utils";

export default function EmployeeDashboard() {
  const { user } = useAuth();

  const { data: stats, loading: statsLoading } = useAsync(
    () => api.get("/dashboard/stats").then((r) => r.data),
    [],
  );
  const { data: recent, loading: ticketsLoading } = useAsync(
    () => api.get("/tickets", { params: { scope: "mine" } }).then((r) => r.data.slice(0, 6)),
    [],
  );

  if (statsLoading || ticketsLoading) {
    return (
      <div className="p-8 flex items-center gap-2 mono-label">
        <CircleNotch className="animate-spin" /> Loading…
      </div>
    );
  }

  const kpis = [
    { label: "My Tickets", value: stats?.total    ?? 0, hint: "All time" },
    { label: "Active",     value: stats?.active   ?? 0, hint: "Open · In Progress · Pending" },
    { label: "Resolved",   value: stats?.resolved ?? 0, hint: "Awaiting closure" },
    { label: "Closed",     value: stats?.closed   ?? 0, hint: "Done" },
  ];

  return (
    <div className="p-6 md:p-8 max-w-[1200px]" data-testid="employee-dashboard-page">
      <div
        className="card-flat p-5 mb-6 flex items-center justify-between"
        style={{ background: "linear-gradient(110deg, #F5E9D4 0%, #FAF3E3 100%)", borderColor: "#E8D5A8" }}
      >
        <div>
          <div className="mono-label" style={{ color: "#8B6A1E" }}>Employee Portal · Your Requests</div>
          <h1 className="text-3xl md:text-4xl font-semibold mt-1" style={{ fontFamily: "Cabinet Grotesk", color: "#3A2D0E", letterSpacing: "-0.02em" }}>
            Good {greeting()}, {user?.name?.split(" ")[0]}.
          </h1>
          <p className="text-sm mt-1" style={{ color: "#6B5A32" }}>
            Need something from HR, Finance, Training, or another team? Raise a ticket and we'll take it from there.
          </p>
        </div>
        <NavLink
          to="/tickets/new"
          className="flex items-center gap-2 px-5 py-3 rounded-md text-sm font-medium"
          style={{ background: "#B8722D", color: "#FAF9F6" }}
          data-testid="employee-new-ticket-cta"
        >
          <Plus size={15} weight="bold" /> Raise a Ticket
        </NavLink>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {kpis.map((k) => (
          <div key={k.label} className="stat-card" data-testid={`emp-kpi-${k.label.toLowerCase().replace(/\s+/g, "-")}`}>
            <div className="mono-label">{k.label}</div>
            <div className="mt-2 text-3xl font-semibold" style={{ fontFamily: "Cabinet Grotesk", letterSpacing: "-0.02em" }}>{k.value}</div>
            <div className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>{k.hint}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <QuickLink to="/my-tickets?scope=assigned_to_me" title="Work on Assigned"  hint="Tickets you need to handle"  count={stats?.assigned_to_me ?? 0} accent testid="qc-assigned" />
        <QuickLink to="/my-tickets?scope=active"         title="Track Active"      hint="See what's in motion"        count={stats?.active   ?? 0}        testid="qc-active" />
        <QuickLink to="/my-tickets?scope=resolved"       title="Confirm Resolved"  hint="Awaiting your closure"       count={stats?.resolved ?? 0}        testid="qc-resolved" />
      </div>

      <div className="card-flat overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
          <div>
            <div className="mono-label">Recent</div>
            <h3 className="text-lg font-medium mt-1" style={{ fontFamily: "Cabinet Grotesk" }}>My Latest Tickets</h3>
          </div>
          <NavLink to="/my-tickets" className="text-sm flex items-center gap-1" style={{ color: "#B8722D" }} data-testid="view-my-tickets">
            View all <ArrowUpRight size={14} />
          </NavLink>
        </div>
        <TicketTable
          tickets={recent || []}
          compact
          emptyTitle="No Tickets Yet"
          emptyDescription="Raise your first ticket and the team will jump on it."
        />
      </div>
    </div>
  );
}

function QuickLink({ to, title, hint, count, accent, testid }) {
  return (
    <NavLink
      to={to}
      className="card-flat p-5 flex items-center justify-between transition-all"
      style={{ borderColor: accent ? "#E8D5A8" : "var(--border-subtle)", background: accent ? "#FDF6EC" : "var(--surface-card)" }}
      data-testid={testid}
    >
      <div>
        <div className="text-sm font-medium" style={{ color: accent ? "#8B6A1E" : "var(--text-primary)", fontFamily: "Cabinet Grotesk" }}>{title}</div>
        <div className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>{hint}</div>
      </div>
      <div className="text-2xl font-semibold" style={{ fontFamily: "Cabinet Grotesk", color: accent ? "#B8722D" : "var(--brand-primary)" }}>{count}</div>
    </NavLink>
  );
}