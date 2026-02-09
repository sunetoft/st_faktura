import { useState } from "react";
import { apiRequest, apiBase } from "../lib/api";

export default function Status() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const check = async () => {
    setLoading(true);
    setStatus(null);
    try {
      const data = await apiRequest("/api/health", { method: "GET" });
      setStatus({ ok: true, message: JSON.stringify(data, null, 2) });
    } catch (error) {
      setStatus({ ok: false, message: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-serif text-3xl text-ink">API status</h1>
        <p className="text-sm text-ink/70">Ping the backend at {apiBase()}.</p>
      </header>
      <button className="btn" type="button" onClick={check} disabled={loading}>
        {loading ? "Checking..." : "Run health check"}
      </button>
      {status ? (
        <pre className={`rounded-xl p-4 text-xs ${status.ok ? "bg-emerald-50 text-emerald-900" : "bg-red-50 text-red-700"}`}>
{status.message}
        </pre>
      ) : null}
    </div>
  );
}
