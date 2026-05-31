import React, { useEffect, useState, useMemo } from "react";
import { useLocation, useNavigate, NavLink } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { useAsync } from "@/hooks/useAsync";
import TicketTable from "@/components/common/TicketTable";
import { CircleNotch, Plus, FunnelSimple } from "@phosphor-icons/react";
import { TICKET_STATUSES, TICKET_PRIORITIES } from "@/lib/constants";

export default function Tickets({ employeeView = false }) {
  const { user }   = useAuth();
  const location   = useLocation();
  const navigate   = useNavigate();

  const filters = useMemo(() => {
    const p = new URLSearchParams(location.search);
    return {
      scope:      p.get("scope")      || "",
      status:     p.get("status")     || "",
      department: p.get("department") || "",
      priority:   p.get("priority")   || "",
      q:          p.get("q")          || "",
    };
  }, [location.search]);

  const { data: tickets, loading: ticketsLoading } = useAsync(
    () => api.get("/tickets", { params: stripEmpty(filters) }).then((r) => r.data),
    [location.search],
  );

  const { data: departments } = useAsync(
    () => api.get("/departments").then((r) => r.data),
    [],
  );

  const pageTitle = useMemo(() => {
    if (employeeView) {
      const map = { resolved: "Resolved Tickets", closed: "Closed Tickets", active: "Active Tickets", assigned_to_me: "Assigned to Me" };
      return map[filters.scope] || "My Tickets";
    }
    const map = {
      unassigned: "Unassigned Tickets", assigned_to_me: "Assigned to Me", escalated: "Escalated Tickets",
      high_priority: "High Priority Tickets", overdue: "Overdue Tickets", active: "Active Tickets",
    };
    if (filters.scope)      return map[filters.scope] || "All Tickets";
    if (filters.status)     return `${filters.status} Tickets`;
    if (filters.department) return `${filters.department} Tickets`;
    return "All Tickets";
  }, [filters, employeeView]);

  const setFilter = (key, value) => {
    const p = new URLSearchParams(location.search);
    value ? p.set(key, value) : p.delete(key);
    navigate(`${location.pathname}?${p.toString()}`);
  };

  const hasFilters = Object.values(filters).some(Boolean);

  return (
    <div className="p-6 md:p-8 max-w-[1600px]" data-testid="tickets-page">
      <div className="flex items-end justify-between mb-6">
        <div>
          <div className="mono-label mb-2">
            {!employeeView && user?.role === "admin" ? "Queue" : "Personal"} · {tickets?.length ?? 0} {tickets?.length === 1 ? "ticket" : "tickets"}
          </div>
          <h1 className="text-3xl font-semibold" style={{ fontFamily: "Cabinet Grotesk" }}>{pageTitle}</h1>
        </div>
        <NavLink to="/tickets/new" className="btn-primary flex items-center gap-1.5" data-testid="new-ticket-button">
          <Plus size={14} weight="bold" /> New Ticket
        </NavLink>
      </div>

      <div className="card-flat p-4 mb-4 flex items-center gap-3 flex-wrap">
        <FunnelSimple size={15} style={{ color: "var(--text-tertiary)" }} />
        <FilterSelect value={filters.status}     onChange={(v) => setFilter("status", v)}     options={TICKET_STATUSES}    placeholder="All Status"      width={150} testid="filter-status" />
        <FilterSelect value={filters.priority}   onChange={(v) => setFilter("priority", v)}   options={TICKET_PRIORITIES}  placeholder="All Priority"    width={150} testid="filter-priority" />
        {!employeeView && (
          <FilterSelect value={filters.department} onChange={(v) => setFilter("department", v)} options={(departments || []).map((d) => d.name)} placeholder="All Departments" width={180} testid="filter-department" />
        )}
        <SearchInput defaultValue={filters.q} onSearch={(v) => setFilter("q", v)} />
        {hasFilters && (
          <button onClick={() => navigate(location.pathname)} className="text-xs underline" style={{ color: "var(--text-tertiary)" }} data-testid="clear-filters">
            Clear filters
          </button>
        )}
      </div>

      <div className="card-flat overflow-hidden">
        {ticketsLoading ? (
          <div className="p-10 flex items-center gap-2 mono-label justify-center">
            <CircleNotch className="animate-spin" /> Loading…
          </div>
        ) : (
          <TicketTable tickets={tickets || []} />
        )}
      </div>
    </div>
  );
}

function FilterSelect({ value, onChange, options, placeholder, width, testid }) {
  return (
    <select
      data-testid={testid}
      className="input-plain"
      style={{ width }}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="">{placeholder}</option>
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  );
}

function SearchInput({ defaultValue, onSearch }) {
  const [val, setVal] = useState(defaultValue);
  useEffect(() => { setVal(defaultValue); }, [defaultValue]);
  return (
    <input
      data-testid="filter-search"
      className="input-plain"
      style={{ width: 220 }}
      placeholder="Search by title, code…"
      value={val}
      onChange={(e) => setVal(e.target.value)}
      onKeyDown={(e) => { if (e.key === "Enter") onSearch(val); }}
    />
  );
}

function stripEmpty(obj) {
  return Object.fromEntries(Object.entries(obj).filter(([, v]) => v));
}
