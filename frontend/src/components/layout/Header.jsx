import React from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { MagnifyingGlass, Bell } from "@phosphor-icons/react";

export default function Header() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const handleSearch = (e) => {
    if (e.key === "Enter" && e.currentTarget.value.trim()) {
      const q = encodeURIComponent(e.currentTarget.value.trim());
      const dest = user?.role === "admin" ? `/tickets?q=${q}` : `/my-tickets?q=${q}`;
      navigate(dest);
      e.currentTarget.value = "";
    }
  };

  return (
    <header
      className="sticky top-0 z-10 flex items-center gap-4 px-6 py-3"
      style={{
        background: "rgba(250,249,246,0.85)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border-subtle)",
        height: 60,
      }}
    >
      <div className="flex-1 max-w-md relative">
        <MagnifyingGlass
          size={14}
          style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}
        />
        <input
          data-testid="global-search"
          className="input-plain"
          placeholder="Search tickets, code, assignee…"
          style={{ paddingLeft: 32, height: 36 }}
          onKeyDown={handleSearch}
        />
      </div>
      <button
        className="p-2 rounded transition-colors"
        style={{ color: "var(--text-secondary)" }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "#fff")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
        data-testid="notifications-button"
        title="Notifications"
      >
        <Bell size={18} />
      </button>
      <div className="mono-label">
        {new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "2-digit" })}
      </div>
    </header>
  );
}
