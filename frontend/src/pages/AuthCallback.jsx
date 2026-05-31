import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export default function AuthCallback() {
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState("Establishing session…");

  useEffect(() => {
    let cancelled = false;

    async function complete() {
      try {
        const user = await refresh();
        if (cancelled) return;
        if (user) {
          navigate("/dashboard", { replace: true });
        } else {
          setStatus("Sign-in failed. Redirecting…");
          setTimeout(() => navigate("/login?error=auth_failed", { replace: true }), 1200);
        }
      } catch {
        if (!cancelled) {
          setStatus("Sign-in failed. Redirecting…");
          setTimeout(() => navigate("/login?error=auth_failed", { replace: true }), 1200);
        }
      }
    }

    complete();
    return () => { cancelled = true; };
  }, [refresh, navigate]);

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ background: "var(--bg-app)" }}
      data-testid="auth-callback-page"
    >
      <div className="text-center">
        <div className="mono-label mb-3">Signing in</div>
        <div className="text-2xl font-semibold mb-2" style={{ fontFamily: "Cabinet Grotesk" }}>
          {status}
        </div>
        <div className="text-sm" style={{ color: "var(--text-secondary)" }}>
          Please wait while we verify your session.
        </div>
      </div>
    </div>
  );
}
