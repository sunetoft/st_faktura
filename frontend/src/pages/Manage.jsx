import { useEffect, useState } from "react";
import { apiRequest } from "../lib/api";

export default function Manage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const [source, setSource] = useState("local");
  const [currentNumber, setCurrentNumber] = useState(784);
  const [nextNumber, setNextNumber] = useState(785);

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

  useEffect(() => {
    loadInvoiceNumber();
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
      <div className="rounded-2xl border border-sand/70 bg-white/70 p-4 text-xs text-ink/70">
        PDFs are saved as <strong>faktura_&lt;number&gt;_&lt;yyyymmdd&gt;.pdf</strong> (example: faktura_811_20251231.pdf).
      </div>
    </div>
  );
}
