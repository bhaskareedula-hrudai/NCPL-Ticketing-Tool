import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { initials } from "@/lib/utils";
import {
  CircleNotch, FloppyDisk, WhatsappLogo,
  CheckCircle, XCircle, QrCode, SignOut,
} from "@phosphor-icons/react";

export default function Settings() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [waStatus, setWaStatus] = useState({ state: "stopped", qr: null, error: null, greenApiReady: false });
  const pollRef = useRef(null);

  const [instanceId, setInstanceId] = useState("");
  const [token, setToken] = useState("");
  const [tokenMasked, setTokenMasked] = useState("");
  const [showToken, setShowToken] = useState(false);
  const [phoneMap, setPhoneMap] = useState("");
  const [loadingWa, setLoadingWa] = useState(false);
  const [savingWa, setSavingWa] = useState(false);
  const [savingPhoneMap, setSavingPhoneMap] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [showWaWeb, setShowWaWeb] = useState(false);

  useEffect(() => {
    if (!isAdmin) return;
    const poll = async () => {
      try {
        const r = await api.get("/settings/whatsapp/status");
        setWaStatus(r.data);
      } catch (_) {}
    };
    poll();
    pollRef.current = setInterval(poll, 4000);
    return () => clearInterval(pollRef.current);
  }, [isAdmin]);

  useEffect(() => {
    if (!isAdmin) return;
    setLoadingWa(true);
    api.get("/settings/whatsapp")
      .then((r) => {
        setInstanceId(r.data.instance_id || "");
        setToken("");
        setTokenMasked(r.data.token_masked || "");
        setPhoneMap(r.data.phone_map || "");
      })
      .catch(() => {})
      .finally(() => setLoadingWa(false));
  }, [isAdmin]);

  const handleLogout = async () => {
    if (!window.confirm("This will log out WhatsApp Web and delete the saved session. You will need to scan QR again.")) return;
    try {
      await api.post("/settings/whatsapp/logout");
      setWaStatus((s) => ({ ...s, state: "stopped", qr: null }));
      toast.success("WhatsApp session cleared");
    } catch (_) {
      toast.error("Failed to logout");
    }
  };

  const handleSaveGreenApi = async (e) => {
    e.preventDefault();
    setSavingWa(true);
    try {
      await api.patch("/settings/whatsapp", {
        instance_id: instanceId,
        ...(token ? { token } : {}),
      });
      toast.success("Green API credentials saved");
      setTestResult(null);
      const r = await api.get("/settings/whatsapp");
      setTokenMasked(r.data.token_masked || "");
      setToken("");
      setShowToken(false);
      const s = await api.get("/settings/whatsapp/status");
      setWaStatus(s.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to save");
    } finally {
      setSavingWa(false);
    }
  };

  const handleSavePhoneMap = async () => {
    setSavingPhoneMap(true);
    try {
      await api.patch("/settings/whatsapp", { phone_map: phoneMap });
      toast.success("Phone map saved");
      setTestResult(null);
    } catch (_) {
      toast.error("Failed to save phone map");
    } finally {
      setSavingPhoneMap(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await api.post("/settings/whatsapp/test");
      setTestResult({ ok: r.data.ok, message: r.data.message });
    } catch (e) {
      setTestResult({ ok: false, message: e.response?.data?.detail || "Test failed" });
    } finally {
      setTesting(false);
    }
  };

  const isConnected = waStatus.state === "connected";
  const greenReady = waStatus.greenApiReady;
  const canTest = isConnected || greenReady;

  let badgeText, badgeColor;
  if (isConnected) { badgeText = "WhatsApp Web ✓"; badgeColor = "#22c55e"; }
  else if (greenReady) { badgeText = "Green API ✓"; badgeColor = "#22c55e"; }
  else { badgeText = "Not configured"; badgeColor = "#888"; }

  return (
    <div className="p-6 md:p-8 max-w-3xl" data-testid="settings-page">
      <div className="mb-6">
        <div className="mono-label">Account</div>
        <h1 className="text-3xl font-semibold mt-1" style={{ fontFamily: "Cabinet Grotesk" }}>Settings</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          Workspace preferences &amp; profile details.
        </p>
      </div>

      <div className="card-flat p-6 mb-4">
        <div className="mono-label mb-4">Your Profile</div>
        <div className="flex items-center gap-4">
          <div style={{ width: 54, height: 54, borderRadius: "50%", background: "var(--brand-primary)", color: "#FAF9F6", display: "grid", placeItems: "center", fontSize: 18, fontWeight: 600, overflow: "hidden" }}>
            {user?.picture ? (
              <img src={user.picture} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            ) : initials(user?.name)}
          </div>
          <div>
            <div style={{ fontWeight: 500 }}>{user?.name}</div>
            <div className="text-sm" style={{ color: "var(--text-secondary)" }}>{user?.email}</div>
            <div className="mono-label mt-1">{user?.role}{user?.department ? ` · ${user.department}` : ""}</div>
          </div>
        </div>
      </div>

      <div className="card-flat p-6 mb-4">
        <div className="mono-label mb-2">Workspace</div>
        <div className="text-sm" style={{ color: "var(--text-secondary)" }}>
          NCPL Internal Ticketing · v2. Authentication via Google OAuth. Sessions valid for 7 days.
        </div>
      </div>

      {isAdmin && (
        <div className="card-flat p-6" style={{ borderLeft: "3px solid #25D366" }}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <WhatsappLogo size={18} style={{ color: "#25D366" }} />
              <div className="mono-label">WhatsApp Notifications</div>
            </div>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{ background: badgeColor + "22", color: badgeColor }}>
              {badgeText}
            </span>
          </div>

          {loadingWa ? (
            <div className="flex items-center gap-2 mono-label text-xs mb-4">
              <CircleNotch className="animate-spin" size={12} /> Loading…
            </div>
          ) : (
            <>
              <div className="p-4 rounded-lg mb-4" style={{ background: "var(--bg-subtle)", border: "1px solid var(--border-subtle)" }}>
                <div className="mono-label text-xs mb-3">Green API Credentials</div>
                <form onSubmit={handleSaveGreenApi}>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                    <div>
                      <label className="text-xs mono-label mb-1 block">Instance ID</label>
                      <input
                        type="text"
                        placeholder="e.g. 7107641724"
                        value={instanceId}
                        onChange={(e) => setInstanceId(e.target.value)}
                        className="w-full border rounded-md px-3 py-2 text-sm"
                        style={{ borderColor: "var(--border-subtle)", background: "var(--bg-app)", color: "var(--text-primary)" }}
                      />
                    </div>
                    <div>
                      <label className="text-xs mono-label mb-1 block">
                        API Token
                        {tokenMasked && !showToken && (
                          <button type="button" onClick={() => setShowToken(true)} className="ml-2 text-xs" style={{ color: "var(--brand-primary)" }}>
                            change
                          </button>
                        )}
                      </label>
                      {showToken || !tokenMasked ? (
                        <input
                          type="text"
                          placeholder="Paste API token"
                          value={token}
                          onChange={(e) => setToken(e.target.value)}
                          className="w-full border rounded-md px-3 py-2 text-sm"
                          style={{ borderColor: "var(--border-subtle)", background: "var(--bg-app)", color: "var(--text-primary)" }}
                        />
                      ) : (
                        <input
                          type="text"
                          value={tokenMasked}
                          disabled
                          className="w-full border rounded-md px-3 py-2 text-sm"
                          style={{ borderColor: "var(--border-subtle)", background: "var(--bg-subtle)", color: "var(--text-tertiary)" }}
                        />
                      )}
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={savingWa}
                    className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium"
                    style={{ background: "var(--brand-primary)", color: "#FAF9F6" }}
                  >
                    {savingWa ? <CircleNotch size={14} className="animate-spin" /> : <FloppyDisk size={14} />}
                    {savingWa ? "Saving…" : "Save Credentials"}
                  </button>
                </form>
              </div>

              <div className="mb-4">
                <label className="text-xs mono-label mb-1 block">Phone Map</label>
                <input
                  type="text"
                  placeholder="Jayalakshmi:+919876543210,Bhuvana:+919876543211"
                  value={phoneMap}
                  onChange={(e) => setPhoneMap(e.target.value)}
                  className="w-full border rounded-md px-3 py-2 text-sm"
                  style={{ borderColor: "var(--border-subtle)", background: "var(--bg-app)", color: "var(--text-primary)" }}
                />
                <p className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>
                  Format: <code>Name:+PhoneNumber</code> — comma-separated. Names must match assignee names exactly.
                </p>
              </div>

              <div className="flex items-center gap-3 flex-wrap mb-4">
                <button
                  onClick={handleSavePhoneMap}
                  disabled={savingPhoneMap}
                  className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium"
                  style={{ background: "var(--brand-primary)", color: "#FAF9F6" }}
                >
                  {savingPhoneMap ? <CircleNotch size={14} className="animate-spin" /> : <FloppyDisk size={14} />}
                  {savingPhoneMap ? "Saving…" : "Save Phone Map"}
                </button>
                <button
                  onClick={handleTest}
                  disabled={testing || !canTest}
                  className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium"
                  style={{ background: "#25D366", color: "#fff", opacity: (testing || !canTest) ? 0.5 : 1 }}
                >
                  {testing ? <CircleNotch size={14} className="animate-spin" /> : <WhatsappLogo size={14} />}
                  {testing ? "Sending…" : "Send Test Message"}
                </button>
                {!canTest && (
                  <span className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                    Save credentials above to enable test
                  </span>
                )}
                {testResult && (
                  <div className="flex items-center gap-1.5 text-sm" style={{ color: testResult.ok ? "#22c55e" : "#EA4335" }}>
                    {testResult.ok ? <CheckCircle size={16} /> : <XCircle size={16} />}
                    {testResult.message}
                  </div>
                )}
              </div>

              <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 12 }}>
                <button onClick={() => setShowWaWeb((v) => !v)} className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                  {showWaWeb ? "▾" : "▸"} WhatsApp Web (self-hosted only — not available on Vercel)
                </button>
                {showWaWeb && (
                  <div className="mt-3 p-4 rounded-lg" style={{ background: "var(--bg-subtle)", border: "1px solid var(--border-subtle)" }}>
                    <div className="flex items-center gap-2 mb-2">
                      <QrCode size={16} style={{ color: "var(--text-secondary)" }} />
                      <span className="text-sm font-medium">WhatsApp Web</span>
                      <span className="text-xs px-2 py-0.5 rounded-full ml-auto" style={{ background: isConnected ? "#22c55e22" : "#88888822", color: isConnected ? "#22c55e" : "#888" }}>
                        {isConnected ? "Connected ✓" : waStatus.state}
                      </span>
                    </div>
                    {(waStatus.state === "stopped" || waStatus.state === "connecting") && (
                      <div className="text-sm" style={{ color: "var(--text-tertiary)" }}>
                        WhatsApp Web is not running. It requires a persistent server — it does not work on Vercel. Use Green API above instead.
                      </div>
                    )}
                    {waStatus.state === "error" && (
                      <div className="text-sm p-3 rounded" style={{ background: "#fef2f2", color: "#EA4335" }}>
                        <strong>Setup required:</strong>
                        <pre className="mt-1 text-xs">pip install playwright{"\n"}python -m playwright install chromium</pre>
                        {waStatus.error && <div className="mt-1 text-xs opacity-70">{waStatus.error}</div>}
                      </div>
                    )}
                    {waStatus.state === "qr" && waStatus.qr && (
                      <div>
                        <p className="text-sm mb-3" style={{ color: "var(--text-secondary)" }}>
                          Open WhatsApp → Linked Devices → Link a Device → scan this QR code.
                        </p>
                        <img src={waStatus.qr} alt="WhatsApp QR Code" style={{ width: 220, height: 220, borderRadius: 8, border: "4px solid #fff" }} />
                      </div>
                    )}
                    {isConnected && (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm" style={{ color: "#22c55e" }}>
                          <CheckCircle size={16} /> Connected and ready.
                        </div>
                        <button onClick={handleLogout} className="flex items-center gap-1 text-xs px-2 py-1 rounded" style={{ color: "var(--text-tertiary)", border: "1px solid var(--border-subtle)" }}>
                          <SignOut size={12} /> Log out
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}