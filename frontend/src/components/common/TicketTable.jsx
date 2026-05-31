import React from "react";
import { useNavigate, NavLink } from "react-router-dom";
import { StatusBadge, PriorityBadge } from "./Badges";
import { timeAgo, initials } from "@/lib/utils";
import EmptyState from "./EmptyState";
import { Plus } from "@phosphor-icons/react";

/**
 * Shared ticket list table used across Dashboard, Tickets, and MyTickets pages.
 * Columns are always: Code · Title · Dept · Priority · Status · Assignee · Requester · Updated
 * Pass `compact` to hide Assignee/Requester columns for dashboard previews.
 */
export default function TicketTable({ tickets, compact = false, emptyTitle = "Empty Queue", emptyDescription = "No tickets match these filters." }) {
  const navigate = useNavigate();

  if (tickets.length === 0) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        action={
          <NavLink to="/tickets/new" className="btn-primary inline-flex items-center gap-1.5">
            <Plus size={14} /> Create the first ticket
          </NavLink>
        }
      />
    );
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="mono-label" style={{ textAlign: "left" }}>
          <th className="py-3 px-4">Code</th>
          <th className="py-3 px-4">Title</th>
          <th className="py-3 px-4">Dept</th>
          <th className="py-3 px-4">Priority</th>
          <th className="py-3 px-4">Status</th>
          {!compact && <th className="py-3 px-4">Assignee</th>}
          {!compact && <th className="py-3 px-4">Requester</th>}
          <th className="py-3 px-4">Updated</th>
        </tr>
      </thead>
      <tbody>
        {tickets.map((t) => (
          <tr
            key={t.id}
            className="row-hover cursor-pointer"
            style={{ borderTop: "1px solid var(--border-subtle)" }}
            onClick={() => navigate(`/tickets/${t.id}`)}
            data-testid={`ticket-row-${t.code}`}
          >
            <td className="py-3 px-4" style={{ fontFamily: "IBM Plex Mono", fontSize: 12, color: "var(--text-secondary)" }}>
              {t.code}
            </td>
            <td className="py-3 px-4">
              <div className="flex items-center gap-2">
                <span style={{ fontWeight: 500, color: "var(--text-primary)" }}>{t.title}</span>
                {t.is_escalated && (
                  <span className="badge-status" style={{ background: "#FDF0EF", color: "#D9534F" }}>Escalated</span>
                )}
                {t.attachments_count > 0 && (
                  <span className="mono-label" style={{ fontSize: 10 }}>📎 {t.attachments_count}</span>
                )}
              </div>
            </td>
            <td className="py-3 px-4" style={{ color: "var(--text-secondary)" }}>{t.department}</td>
            <td className="py-3 px-4"><PriorityBadge priority={t.priority} /></td>
            <td className="py-3 px-4"><StatusBadge status={t.status} /></td>
            {!compact && (
              <td className="py-3 px-4" style={{ color: "var(--text-secondary)" }}>
                {t.assignee_name ? (
                  <div className="flex items-center gap-2">
                    <Avatar name={t.assignee_name} />
                    <span>{t.assignee_name}</span>
                  </div>
                ) : (
                  <span className="mono-label" style={{ fontSize: 10 }}>Unassigned</span>
                )}
              </td>
            )}
            {!compact && (
              <td className="py-3 px-4" style={{ color: "var(--text-secondary)" }}>{t.created_by_name}</td>
            )}
            <td className="py-3 px-4 text-xs" style={{ color: "var(--text-tertiary)" }}>{timeAgo(t.updated_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Avatar({ name }) {
  return (
    <div style={{ width: 22, height: 22, borderRadius: "50%", background: "var(--brand-primary)", color: "#FAF9F6", fontSize: 10, display: "grid", placeItems: "center" }}>
      {initials(name)}
    </div>
  );
}
