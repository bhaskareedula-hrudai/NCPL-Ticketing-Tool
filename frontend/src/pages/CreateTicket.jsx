import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAsync } from "@/hooks/useAsync";
import { TICKET_PRIORITIES } from "@/lib/constants";
import { toast } from "sonner";
import { CircleNotch, ArrowLeft, WarningCircle } from "@phosphor-icons/react";

const INITIAL_FORM = { title: "", description: "", department: "", priority: "Medium", assignee_name: "" };

export default function CreateTicket() {
  const navigate = useNavigate();
  const [form, setForm]         = useState(INITIAL_FORM);
  const [files, setFiles]       = useState([]);
  const [submitting, setSubmit] = useState(false);

  const { data: departments = [], loading: deptsLoading, error: deptsError } = useAsync(
    () => api.get("/departments").then((r) => {
      const depts = r.data;
      if (depts[0]) setForm((f) => ({ ...f, department: depts[0].name }));
      return depts;
    }),
    [],
  );

  const { data: assignees = [] } = useAsync(
    () =>
      form.department
        ? api.get(`/departments/${encodeURIComponent(form.department)}/members`).then((r) => r.data)
        : Promise.resolve([]),
    [form.department],
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.description.trim() || !form.department) {
      toast.error("Please fill title, description, and department.");
      return;
    }
    setSubmit(true);
    try {
      const payload = { ...form };
      if (!payload.assignee_name) delete payload.assignee_name;
      const res    = await api.post("/tickets", payload);
      const ticket = res.data;
      for (const file of files) {
        const fd = new FormData();
        fd.append("file", file);
        await api.post(`/tickets/${ticket.id}/attachments`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      }
      toast.success(`Ticket ${ticket.code} created.`);
      navigate(`/tickets/${ticket.id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create ticket");
    } finally {
      setSubmit(false);
    }
  };

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleDeptChange = (e) =>
    setForm((f) => ({ ...f, department: e.target.value, assignee_name: "" }));

  if (deptsLoading) {
    return (
      <div className="p-6 md:p-8 flex items-center gap-2 mono-label">
        <CircleNotch className="animate-spin" size={14} /> Loading…
      </div>
    );
  }

  if (deptsError) {
    return (
      <div className="p-6 md:p-8 max-w-3xl">
        <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 mono-label mb-4 hover:underline">
          <ArrowLeft size={12} /> Back
        </button>
        <div className="card-flat p-6 flex items-center gap-3" style={{ color: "var(--status-urgent)" }}>
          <WarningCircle size={20} />
          <div>
            <div className="font-medium">Failed to load departments</div>
            <div className="text-sm mt-0.5" style={{ color: "var(--text-secondary)" }}>
              Please check your connection and{" "}
              <button className="underline" onClick={() => window.location.reload()}>try again</button>.
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 max-w-3xl" data-testid="create-ticket-page">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 mono-label mb-4 hover:underline" data-testid="back-button">
        <ArrowLeft size={12} /> Back
      </button>

      <div className="mb-6">
        <div className="mono-label">New Ticket</div>
        <h1 className="text-3xl font-semibold mt-1" style={{ fontFamily: "Cabinet Grotesk" }}>Raise a request</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          Provide a clear title and context. Route to the right department for fastest response.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card-flat p-6 space-y-5">
        <FormField label="Title">
          <input data-testid="ticket-title-input" className="input-plain" placeholder="e.g. Laptop overheating during calls" value={form.title} onChange={set("title")} />
        </FormField>

        <FormField label="Description">
          <textarea
            data-testid="ticket-description-input"
            className="input-plain"
            rows={6}
            style={{ resize: "vertical" }}
            placeholder="Add as much detail as possible — steps to reproduce, expected vs actual, impact, urgency…"
            value={form.description}
            onChange={set("description")}
          />
        </FormField>

        <div className="grid grid-cols-2 gap-4">
          <FormField label="Department">
            <select data-testid="ticket-department-select" className="input-plain" value={form.department} onChange={handleDeptChange}>
              {departments.map((d) => <option key={d.id} value={d.name}>{d.name}</option>)}
            </select>
          </FormField>
          <FormField label="Priority">
            <select data-testid="ticket-priority-select" className="input-plain" value={form.priority} onChange={set("priority")}>
              {TICKET_PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </FormField>
        </div>

        <FormField label="Assign To">
          <select
            data-testid="ticket-assignee-select"
            className="input-plain"
            value={form.assignee_name}
            onChange={set("assignee_name")}
            disabled={assignees.length === 0}
          >
            <option value="">— Select assignee (optional) —</option>
            {assignees.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
          {assignees.length === 0 && form.department && (
            <p className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>
              No assignees configured for {form.department}.
            </p>
          )}
        </FormField>

        <FormField label="Attachments (optional, max 15 MB each)">
          <input
            data-testid="ticket-attachments-input"
            type="file"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files))}
            className="text-sm"
            style={{ color: "var(--text-secondary)" }}
          />
          {files.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {files.map((f) => (
                <span key={`${f.name}-${f.size}`} className="badge-status" style={{ background: "var(--surface-hover)", color: "var(--text-primary)" }}>{f.name}</span>
              ))}
            </div>
          )}
        </FormField>

        <div className="flex justify-end gap-2 pt-2" style={{ borderTop: "1px solid var(--border-subtle)" }}>
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary" data-testid="cancel-button">Cancel</button>
          <button type="submit" disabled={submitting} className="btn-primary flex items-center gap-1.5" data-testid="submit-ticket-button">
            {submitting && <CircleNotch className="animate-spin" size={14} />}
            {submitting ? "Creating…" : "Create Ticket"}
          </button>
        </div>
      </form>
    </div>
  );
}

function FormField({ label, children }) {
  return (
    <div>
      <label className="mono-label block mb-2">{label}</label>
      {children}
    </div>
  );
}