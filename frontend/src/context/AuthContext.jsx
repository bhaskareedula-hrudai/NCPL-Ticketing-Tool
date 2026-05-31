import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [loading, setLoading] = useState(true);

  // Returns fetched user so callers (AuthCallback) can act on it immediately
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/auth/me");
      setUser(res.data);
      return res.data;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // proceed regardless
    }
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}
