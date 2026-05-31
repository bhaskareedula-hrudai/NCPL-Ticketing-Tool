import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";

import { AuthProvider, useAuth } from "@/context/AuthContext";
import AppLayout from "@/components/layout/AppLayout";

import Login            from "@/pages/Login";
import AuthCallback     from "@/pages/AuthCallback";
import Dashboard        from "@/pages/Dashboard";
import EmployeeDashboard from "@/pages/EmployeeDashboard";
import Tickets          from "@/pages/Tickets";
import MyTickets        from "@/pages/MyTickets";
import TicketDetail     from "@/pages/TicketDetail";
import CreateTicket     from "@/pages/CreateTicket";
import Employees        from "@/pages/Employees";
import Departments      from "@/pages/Departments";
import Reports          from "@/pages/Reports";
import Settings         from "@/pages/Settings";

import "./App.css";

function RequireAdmin({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/dashboard" replace />;
  return children;
}

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={user ? "/dashboard" : "/login"} replace />;
}

function RoleDashboard() {
  const { user } = useAuth();
  if (!user) return null;
  return user.role === "admin" ? <Dashboard /> : <EmployeeDashboard />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login"         element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />

      <Route element={<AppLayout />}>
        <Route path="/dashboard"   element={<RoleDashboard />} />
        <Route path="/tickets"     element={<RequireAdmin><Tickets /></RequireAdmin>} />
        <Route path="/tickets/new" element={<CreateTicket />} />
        <Route path="/tickets/:id" element={<TicketDetail />} />
        <Route path="/my-tickets"  element={<MyTickets />} />
        <Route path="/employees"   element={<RequireAdmin><Employees /></RequireAdmin>} />
        <Route path="/departments" element={<RequireAdmin><Departments /></RequireAdmin>} />
        <Route path="/reports"     element={<RequireAdmin><Reports /></RequireAdmin>} />
        <Route path="/settings"    element={<Settings />} />
      </Route>

      <Route path="/"  element={<RootRedirect />} />
      <Route path="*"  element={<Navigate to="/" replace />} />
    </Routes>
  );
}

const TOAST_STYLE = {
  style: {
    background: "#FFFFFF",
    border: "1px solid #E5E2DC",
    color: "#1C1C1C",
    fontFamily: "IBM Plex Sans",
    fontSize: 13,
  },
};

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster position="top-right" toastOptions={TOAST_STYLE} />
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
