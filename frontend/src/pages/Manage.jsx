import { useEffect, useState } from "react";
import { apiRequest } from "../lib/api";

export default function Manage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const [source, setSource] = useState("local");
  const [currentNumber, setCurrentNumber] = useState(784);
  const [nextNumber, setNextNumber] = useState(785);

  // Override date state
  const [overrideEnabled, setOverrideEnabled] = useState(false);
  const [overrideDate, setOverrideDate] = useState("");
  const [overrideSaving, setOverrideSaving] = useState(false);
  const [overrideStatus, setOverrideStatus] = useState(null);

  const loadInvoiceNumber = async () => {
    setLoading(true);
    setStatus(null);
    try {
      const data = await apiRequest("/invoice-number");
      setCurrentNumber(Number(data.current_invoice_number || 784));
      setNextNumber(Number(data.next_invoice_number || 785));
      setSource(data.source || "local");
    } catch (error) {
      setStatus({ ok: false, message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const loadOverrideDate = async () => {
    try {
      const data = await apiRequest("/override-date");
      setOverrideEnabled(data.enabled || false);
      setOverrideDate(data.override_date || "");
    } catch (error) {
      setOverrideStatus({ ok: false, message: error.message });
    }
  };

  useEffect(() => {
    loadInvoiceNumber();
    loadOverrideDate();
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setStatus(null);
    try {
      const payload = { next_invoice_number: Number(nextNumber) };
      const data = await apiRequest("/invoice-number", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      setCurrentNumber(Number(data.current_invoice_number || 784));
      setNextNumber(Number(data.next_invoice_number || 785));
      setSource(data.source || "local");
      setStatus({ ok: true, message: "Invoice number updated." });
    } catch (error) {
      setStatus({ ok: false, message: error.message });
    } finally {
      setSaving(false);
    }
  };

  const submitOverride = async (event) => {
    event.preventDefault();
    setOverrideSaving(true);
    setOverrideStatus(null);
    try {
      const payload = { enabled: overrideEnabled, override_date: overrideDate || null };
      const data = await apiRequest("/override-date", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      setOverrideEnabled(data.enabled || false);
      setOverrideDate(data.override_date || "");
      setOverrideStatus({
        ok: true,
        message: data.enabled
          ? `Override date active — new invoices will use ${data.override_date}.`
          : "Override date disabled — new invoices use today's date.",
      });
    } catch (error) {
      setOverrideStatus({ ok: false, message: error.message });
    } finally {
      setOverrideSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-serif text-3xl text-ink">Manage</h1>
        <p className="text-sm text-ink/70">Set the next consecutive invoice number.</p>
      </header>
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-sand/70 bg-white/70 p-4 text-sm text-ink/70">
          <p>Storage: <span className="font-semibold text-ink">{source}</span></p>
          <p>Current invoice number: <span className="font-semibold text-ink">{currentNumber}</span></p>
        </div>
        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wide text-ink/60">Next invoice number</label>
          <input
            className="input"
            type="number"
            min="1"
            value={nextNumber}
            onChange={(event) => setNextNumber(event.target.value)}
            disabled={loading}
            required
          />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn" type="submit" disabled={saving || loading}>
            {saving ? "Saving..." : "Save"}
          </button>
          <button className="btn-secondary" type="button" onClick={loadInvoiceNumber} disabled={loading}>
            Refresh
          </button>
        </div>
      </form>
      {status ? (
        <pre className={`rounded-xl p-4 text-xs ${status.ok ? "bg-emerald-50 text-emerald-900" : "bg-red-50 text-red-700"}`}>
{status.message}
        </pre>
      ) : null}

      {/* Override Invoice Date Section */}
      <form onSubmit={submitOverride} className="rounded-2xl border border-sand/70 bg-white/70 p-6 space-y-4">
        <div>
          <h2 className="font-serif text-xl text-ink">Override Invoice Date</h2>
          <p className="text-sm text-ink/70">
            When enabled, all new invoices will use the selected date instead of today's date.
            Stays active until turned off.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={overrideEnabled}
              onChange={(event) => setOverrideEnabled(event.target.checked)}
              className="h-5 w-5 rounded border-sand text-ink focus:ring-ink"
            />
            <span className="text-sm font-semibold text-ink">Enable override</span>
          </label>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wide text-ink/60">Invoice date</label>
            <input
              className="input"
              type="date"
              value={overrideDate}
              onChange={(event) => setOverrideDate(event.target.value)}
              disabled={!overrideEnabled}
              required={overrideEnabled}
            />
          </div>
          <button className="btn" type="submit" disabled={overrideSaving}>
            {overrideSaving ? "Saving..." : "Save override"}
          </button>
        </div>
        {overrideEnabled && overrideDate ? (
          <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900">
            ⚠️ Override is <strong>active</strong>. New invoices will be dated <strong>{overrideDate}</strong>.
            Credit memos will also use this date.
          </div>
        ) : null}
        {overrideStatus ? (
          <pre className={`rounded-xl p-4 text-xs ${overrideStatus.ok ? "bg-emerald-50 text-emerald-900" : "bg-red-50 text-red-700"}`}>
{overrideStatus.message}
          </pre>
        ) : null}
      </form>

      <div className="rounded-2xl border border-sand/70 bg-white/70 p-4 text-xs text-ink/70">
        PDFs are saved as <strong>faktura_&lt;number&gt;_&lt;yyyymmdd&gt;.pdf</strong> (example: faktura_811_20251231.pdf).
      </div>
    </div>
  );
}
