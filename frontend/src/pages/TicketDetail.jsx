import React, { useCallback, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api, API_BASE } from "@/lib/api";
import { useAsync } from "@/hooks/useAsync";
import { StatusBadge, PriorityBadge } from "@/components/common/Badges";
import { formatDateTime, timeAgo, initials } from "@/lib/utils";
import { TICKET_STATUSES, TICKET_PRIORITIES } from "@/lib/constants";
import { ArrowLeft, Paperclip, CircleNotch, FireSimple, ArrowCircleRight, CheckCircle } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function TicketDetail() {
  const { id }       = useParams();
  const { user }     = useAuth();
  const navigate     = useNavigate();
  const isAdmin      = user?.role === "admin";

  const { data: ticket, loading, refetch: refetchTicket } = useAsync(
    () => api.get(`/tickets/${id}`).then((r) => r.data),
    [id],
  );
  const { data: comments = [], refetch: refetchComments } = useAsync(
    () => api.get(`/tickets/${id}/comments`).then((r) => r.data),
    [id],
  );
  const { data: attachments = [], refetch: refetchAttachments } = useAsync(
    () => api.get(`/tickets/${id}/attachments`).then((r) => r.data),
    [id],
  );
  const { data: employees = [] } = useAsync(
    () => api.get("/employees/assignable").then((r) => r.data),
    [],
  );
  const { data: departments = [] } = useAsync(
    () => api.get("/departments").then((r) => r.data),
    [],
  );

  const [newComment, setNewComment] = useState("");
  const [isInternal, setIsInternal] = useState(false);
  const [uploading, setUploading]   = useState(false);

  const mutate = useCallback(async (action) => {
    try {
      await action();
      refetchTicket();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Action failed");
    }
  }, [refetchTicket]);

  const changeStatus  = (status)     => mutate(async () => { await api.post(`/tickets/${id}/status`, { status }); toast.success(`Marked as ${status}`); });
  const updateField   = (patch)      => mutate(async () => { await api.patch(`/tickets/${id}`, patch); toast.success("Updated"); });
  const assign        = (assigneeId) => mutate(async () => { await api.post(`/tickets/${id}/assign`, { assignee_id: assigneeId || null }); toast.success("Assignment updated"); });
  const escalate      = ()           => mutate(async () => { await api.post(`/tickets/${id}/escalate`); toast.success("Escalated"); });

  const postComment = async () => {
    if (!newComment.trim()) return;
    try {
      await api.post(`/tickets/${id}/comments`, { body: newComment, is_internal: isInternal });
      setNewComment("");
      setIsInternal(false);
      refetchComments();
      toast.success("Comment added");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to add comment");
    }
  };

  const uploadFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await api.post(`/tickets/${id}/attachments`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      refetchAttachments();
      toast.success("Uploaded");
    } catch {
      toast.error("Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  if (loading) {
    return <div className="p-8 flex items-center gap-2 mono-label"><CircleNotch className="animate-spin" /> Loading…</div>;
  }
  if (!ticket) return <div className="p-8">Ticket not found.</div>;

  const isAssignee           = !isAdmin && ticket.assignee_id === user.user_id;
  const canEmployeeClose     = !isAdmin && ticket.status === "Resolved" && ticket.created_by === user.user_id;
  const employeeWorkStatuses = ["Open", "In Progress", "Pending", "Resolved"];

  return (
    <div className="p-6 md:p-8 max-w-[1400px]" data-testid="ticket-detail-page">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 mono-label mb-4 hover:underline">
        <ArrowLeft size={12} /> Back
      </button>

      <div className="flex items-start justify-between gap-4 mb-6">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="mono-label" style={{ fontSize: 12 }}>{ticket.code}</span>
            <StatusBadge status={ticket.status} />
            <PriorityBadge priority={ticket.priority} />
            {ticket.is_escalated && (
              <span className="badge-status" style={{ background: "#FDF0EF", color: "#D9534F" }}>Escalated</span>
            )}
          </div>
          <h1 className="text-3xl font-semibold" style={{ fontFamily: "Cabinet Grotesk" }} data-testid="ticket-title">
            {ticket.title}
          </h1>
          <div className="mt-2 text-xs" style={{ color: "var(--text-tertiary)" }}>
            Opened by <span style={{ color: "var(--text-secondary)" }}>{ticket.created_by_name}</span> · {formatDateTime(ticket.created_at)} · last updated {timeAgo(ticket.updated_at)}
          </div>
        </div>
        {canEmployeeClose && (
          <button onClick={() => changeStatus("Closed")} className="btn-primary flex items-center gap-1.5" data-testid="close-ticket-button">
            <CheckCircle size={14} /> Confirm &amp; Close
          </button>
        )}
        {isAssignee && (
          <div className="px-3 py-1.5 rounded-md text-xs font-medium" style={{ background: "#FDF6EC", color: "#8B6A1E", border: "1px solid #E8D5A8" }} data-testid="assigned-to-you-badge">
            Assigned to you
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        <div className="space-y-4">
          <div className="card-flat p-5">
            <div className="mono-label mb-2">Description</div>
            <p className="text-sm whitespace-pre-wrap" style={{ color: "var(--text-primary)", lineHeight: 1.65 }}>{ticket.description}</p>
          </div>

          <div className="card-flat p-5">
            <div className="mono-label mb-3">Activity &amp; Comments</div>
            {comments.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>No comments yet. Start the conversation below.</p>
            ) : (
              <ol className="space-y-4">
                {comments.map((c) => (
                  <li key={c.id} className="flex gap-3" data-testid={`comment-${c.id}`}>
                    <div style={{ width: 30, height: 30, flexShrink: 0, borderRadius: "50%", background: c.author_role === "admin" ? "var(--brand-primary)" : "#B8B4A9", color: "#FAF9F6", fontSize: 11, display: "grid", placeItems: "center" }}>
                      {initials(c.author_name)}
                    </div>
                    <div className="flex-1">
                      <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{c.author_name}</span>
                        <span className="mono-label" style={{ fontSize: 9, marginLeft: 4 }}>{c.author_role}</span>
                        {c.is_internal && <span className="ml-2 badge-status" style={{ background: "#FDF6EC", color: "#E6A23C", fontSize: 10 }}>Internal</span>}
                        <span className="ml-2">· {timeAgo(c.created_at)}</span>
                      </div>
                      <div className="text-sm mt-1 whitespace-pre-wrap" style={{ color: "var(--text-primary)", lineHeight: 1.55 }}>{c.body}</div>
                    </div>
                  </li>
                ))}
              </ol>
            )}
            <div className="mt-5 pt-5" style={{ borderTop: "1px solid var(--border-subtle)" }}>
              <textarea
                data-testid="comment-input"
                className="input-plain"
                rows={3}
                placeholder="Add a reply…"
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
              />
              <div className="flex items-center justify-between mt-2">
                {isAdmin ? (
                  <label className="flex items-center gap-2 text-xs" style={{ color: "var(--text-secondary)" }}>
                    <input type="checkbox" checked={isInternal} onChange={(e) => setIsInternal(e.target.checked)} data-testid="internal-note-checkbox" />
                    Internal note (hidden from requester)
                  </label>
                ) : <span />}
                <button onClick={postComment} className="btn-primary" data-testid="post-comment-button">Post Reply</button>
              </div>
            </div>
          </div>

          <div className="card-flat p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="mono-label">Attachments ({attachments.length})</div>
              <label className="btn-secondary flex items-center gap-1.5 cursor-pointer text-xs" data-testid="upload-attachment-label">
                <Paperclip size={13} />
                {uploading ? "Uploading…" : "Attach file"}
                <input type="file" className="hidden" onChange={uploadFile} disabled={uploading} data-testid="upload-attachment-input" />
              </label>
            </div>
            {attachments.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>No files yet.</p>
            ) : (
              <ul className="space-y-2">
                {attachments.map((a) => (
                  <li key={a.id} className="flex items-center justify-between text-sm py-2 px-3 rounded" style={{ background: "var(--bg-app)" }}>
                    <a
                      href={`${API_BASE}/attachments/${a.id}/download`}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-2 hover:underline"
                      style={{ color: "var(--text-primary)" }}
                      data-testid={`attachment-${a.id}`}
                    >
                      <Paperclip size={13} /> {a.filename}
                    </a>
                    <span className="mono-label" style={{ fontSize: 10 }}>{(a.size / 1024).toFixed(0)} KB · {timeAgo(a.created_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <aside className="space-y-4">
          <div className="card-flat p-5">
            <div className="mono-label mb-3">Details</div>
            <div className="space-y-3 text-sm">
              <MetaField label="Status">
                {isAdmin || isAssignee ? (
                  <select className="input-plain" style={{ padding: "6px 10px" }} value={ticket.status} onChange={(e) => changeStatus(e.target.value)} data-testid="status-select">
                    {(isAdmin ? TICKET_STATUSES : employeeWorkStatuses).map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                ) : <StatusBadge status={ticket.status} />}
              </MetaField>

              <MetaField label="Priority">
                {isAdmin ? (
                  <select className="input-plain" style={{ padding: "6px 10px" }} value={ticket.priority} onChange={(e) => updateField({ priority: e.target.value })} data-testid="priority-select">
                    {TICKET_PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                ) : <PriorityBadge priority={ticket.priority} />}
              </MetaField>

              <MetaField label="Department">
                {isAdmin ? (
                  <select className="input-plain" style={{ padding: "6px 10px" }} value={ticket.department} onChange={(e) => updateField({ department: e.target.value })} data-testid="department-select">
                    {departments.map((d) => <option key={d.id} value={d.name}>{d.name}</option>)}
                  </select>
                ) : <span>{ticket.department}</span>}
              </MetaField>

              <MetaField label="Assignee">
                {isAdmin ? (
                  <select className="input-plain" style={{ padding: "6px 10px" }} value={ticket.assignee_id || ""} onChange={(e) => assign(e.target.value)} data-testid="assignee-select">
                    <option value="">Unassigned</option>
                    {employees.map((u) => <option key={u.user_id} value={u.user_id}>{u.name}</option>)}
                  </select>
                ) : <span>{ticket.assignee_name || "Unassigned"}</span>}
              </MetaField>

              <MetaField label="Requester"><span>{ticket.created_by_name}</span></MetaField>
              <MetaField label="Code"><span style={{ fontFamily: "IBM Plex Mono", fontSize: 12 }}>{ticket.code}</span></MetaField>
            </div>

            {isAdmin && !ticket.is_escalated && (
              <button onClick={escalate} className="btn-secondary mt-4 w-full flex items-center justify-center gap-1.5 text-sm" data-testid="escalate-button">
                <FireSimple size={13} /> Escalate
              </button>
            )}
          </div>

          {(isAdmin || isAssignee) && (
            <div className="card-flat p-5">
              <div className="mono-label mb-3">Quick Actions</div>
              <div className="space-y-2">
                {ticket.status !== "In Progress" && (
                  <button onClick={() => changeStatus("In Progress")} className="btn-secondary w-full text-sm flex items-center gap-1.5" data-testid="qa-inprogress">
                    <ArrowCircleRight size={14} /> Move to In Progress
                  </button>
                )}
                {ticket.status !== "Pending" && (
                  <button onClick={() => changeStatus("Pending")} className="btn-secondary w-full text-sm" data-testid="qa-pending">
                    Mark as Pending
                  </button>
                )}
                {ticket.status !== "Resolved" && (
                  <button onClick={() => changeStatus("Resolved")} className="btn-primary w-full text-sm flex items-center justify-center gap-1.5" data-testid="qa-resolved">
                    <CheckCircle size={14} /> Resolve
                  </button>
                )}
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function MetaField({ label, children }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="mono-label" style={{ fontSize: 10 }}>{label}</span>
      <div style={{ minWidth: 160 }}>{children}</div>
    </div>
  );
}
