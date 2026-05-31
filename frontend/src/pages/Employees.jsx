import React, { useState } from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/hooks/useAsync";
import { toast } from "sonner";
import { CircleNotch, UserCircle, UserPlus, Trash } from "@phosphor-icons/react";
import { initials, timeAgo } from "@/lib/utils";

const ROLES = ["admin", "employee"];

export default function Employees() {
  const { data: employees, loading, refetch } = useAsync(
    () => api.get("/employees").then((r) => r.data),
    [],
  );
  const { data: departments = [] } = useAsync(
    () => api.get("/departments").then((r) => r.data),
    [],
  );

  const [showAdd, setShowAdd]       = useState(false);
  const [addEmail, setAddEmail]     = useState("");
  const [addName, setAddName]       = useState("");
  const [addRole, setAddRole]       = useState("employee");
  const [addDept, setAddDept]       = useState("");
  const [adding, setAdding]         = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const update = async (userId, patch) => {
    try {
      await api.patch(`/employees/${userId}`, patch);
      refetch();
      toast.success("Updated");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Update failed");
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    setAdding(true);
    try {
      await api.post("/employees", {
        email: addEmail.trim(),
        name: addName.trim() || undefined,
        role: addRole,
        department: addDept || undefined,
      });
      toast.success(`${addEmail} added successfully`);
      setAddEmail(""); setAddName(""); setAddRole("employee"); setAddDept("");
      setShowAdd(false);
      refetch();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to add employee");
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (userId, name) => {
    if (!window.confirm(`Remove ${name} from the workspace? This will revoke their access.`)) return;
    setDeletingId(userId);
    try {
      await api.delete(`/employees/${userId}`);
      toast.success(`${name} removed`);
      refetch();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-[1400px]" data-testid="employees-page">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="mono-label">Workspace</div>
          <h1 className="text-3xl font-semibold mt-1" style={{ fontFamily: "Cabinet Grotesk" }}>Employees</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            New signups start as Employee. Promote to Admin here. Users appear after their first Google sign-in.
          </p>
        </div>
        <button
          onClick={() => setShowAdd((v) => !v)}
          className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium"
          style={{ background: "var(--brand-primary)", color: "#FAF9F6", whiteSpace: "nowrap" }}
        >
          <UserPlus size={16} />
          Add Employee
        </button>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="card-flat p-5 mb-4"
          style={{ borderLeft: "3px solid var(--brand-primary)" }}>
          <div className="mono-label mb-4">Add New Employee</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
            <div>
              <label className="text-xs mono-label mb-1 block">Email *</label>
              <input type="email" required autoFocus placeholder="employee@company.com"
                value={addEmail} onChange={(e) => setAddEmail(e.target.value)}
                className="w-full border rounded-md px-3 py-2 text-sm"
                style={{ borderColor: "var(--border-subtle)", background: "var(--bg-app)", color: "var(--text-primary)" }} />
            </div>
            <div>
              <label className="text-xs mono-label mb-1 block">Name (optional)</label>
              <input type="text" placeholder="Full name"
                value={addName} onChange={(e) => setAddName(e.target.value)}
                className="w-full border rounded-md px-3 py-2 text-sm"
                style={{ borderColor: "var(--border-subtle)", background: "var(--bg-app)", color: "var(--text-primary)" }} />
            </div>
            <div>
              <label className="text-xs mono-label mb-1 block">Role</label>
              <select value={addRole} onChange={(e) => setAddRole(e.target.value)}
                className="w-full border rounded-md px-3 py-2 text-sm"
                style={{ borderColor: "var(--border-subtle)", background: "var(--bg-app)", color: "var(--text-primary)" }}>
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs mono-label mb-1 block">Department (optional)</label>
              <select value={addDept} onChange={(e) => setAddDept(e.target.value)}
                className="w-full border rounded-md px-3 py-2 text-sm"
                style={{ borderColor: "var(--border-subtle)", background: "var(--bg-app)", color: "var(--text-primary)" }}>
                <option value="">—</option>
                {departments.map((d) => <option key={d.id} value={d.name}>{d.name}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={adding}
              className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium"
              style={{ background: "var(--brand-primary)", color: "#FAF9F6" }}>
              {adding ? <CircleNotch size={14} className="animate-spin" /> : <UserPlus size={14} />}
              {adding ? "Adding…" : "Add Employee"}
            </button>
            <button type="button" onClick={() => setShowAdd(false)}
              className="px-4 py-2 rounded-md text-sm"
              style={{ border: "1px solid var(--border-subtle)", color: "var(--text-secondary)" }}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="card-flat overflow-hidden">
        {loading ? (
          <div className="p-10 flex items-center gap-2 mono-label justify-center">
            <CircleNotch className="animate-spin" /> Loading…
          </div>
        ) : !employees?.length ? (
          <div className="p-10 text-center">
            <UserCircle size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 8px" }} />
            <div className="mono-label">No Employees yet</div>
            <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
              Add an employee above or wait for them to sign in with Google.
            </p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="mono-label" style={{ textAlign: "left" }}>
                <th className="py-3 px-4">Name</th>
                <th className="py-3 px-4">Email</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Department</th>
                <th className="py-3 px-4">Joined</th>
                <th className="py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {employees.map((u) => (
                <tr key={u.user_id} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <div style={{ width: 28, height: 28, borderRadius: "50%", background: "var(--brand-primary)", color: "#FAF9F6", fontSize: 11, display: "grid", placeItems: "center", flexShrink: 0 }}>
                        {initials(u.name)}
                      </div>
                      <span style={{ fontWeight: 500 }}>{u.name}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4" style={{ color: "var(--text-secondary)" }}>{u.email}</td>
                  <td className="py-3 px-4">
                    <select className="input-plain" style={{ padding: "5px 8px", width: 120 }}
                      value={u.role} onChange={(e) => update(u.user_id, { role: e.target.value })}>
                      {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>
                  <td className="py-3 px-4">
                    <select className="input-plain" style={{ padding: "5px 8px", width: 140 }}
                      value={u.department || ""} onChange={(e) => update(u.user_id, { department: e.target.value })}>
                      <option value="">—</option>
                      {departments.map((d) => <option key={d.id} value={d.name}>{d.name}</option>)}
                    </select>
                  </td>
                  <td className="py-3 px-4 text-xs" style={{ color: "var(--text-tertiary)" }}>
                    {timeAgo(u.created_at)}
                  </td>
                  <td className="py-3 px-4">
                    <button onClick={() => handleDelete(u.user_id, u.name)}
                      disabled={deletingId === u.user_id} title="Remove employee"
                      className="flex items-center justify-center rounded p-1.5"
                      style={{ color: "var(--text-tertiary)" }}
                      onMouseEnter={(e) => e.currentTarget.style.color = "#EA4335"}
                      onMouseLeave={(e) => e.currentTarget.style.color = "var(--text-tertiary)"}>
                      {deletingId === u.user_id
                        ? <CircleNotch size={15} className="animate-spin" />
                        : <Trash size={15} />}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}