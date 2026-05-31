import React, { useEffect, useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function AppLayout() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [counts, setCounts]           = useState({});
  const [departments, setDepartments] = useState([]);

  useEffect(() => {
    if (!loading && !user) navigate("/login", { replace: true });
  }, [loading, user, navigate]);

  useEffect(() => {
    if (!user) return;
    Promise.all([api.get("/dashboard/stats"), api.get("/departments")])
      .then(([stats, depts]) => {
        setCounts(stats.data);
        setDepartments(depts.data);
      })
      .catch(() => {});
  }, [user, location.pathname]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <span className="mono-label">Loading…</span>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen" style={{ background: "var(--bg-app)" }}>
      <Sidebar counts={counts} departments={departments} />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 fade-in" data-testid="main-content">
          <Outlet context={{ counts, departments }} />
        </main>
      </div>
    </div>
  );
}
