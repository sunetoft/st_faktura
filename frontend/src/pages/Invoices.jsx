import { useEffect, useMemo, useState } from "react";
import { apiBase, apiRequest } from "../lib/api";

const EXPENSE_EMAIL = "udgift@ebogholderen.dk";

function formatCurrency(value) {
  return new Intl.NumberFormat("da-DK", {
    style: "currency",
    currency: "DKK",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatDate(value) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString("da-DK", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

export default function Invoices() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [sendLoading, setSendLoading] = useState(false);
  const [sendError, setSendError] = useState("");
  const [sendCustomer, setSendCustomer] = useState(true);
  const [sendExpense, setSendExpense] = useState(true);
  const [activeInvoice, setActiveInvoice] = useState(null);

  const loadInvoices = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await apiRequest("/invoices/list");
      setInvoices(Array.isArray(data?.invoices) ? data.invoices : []);
    } catch (err) {
      setError(err?.message || "Failed to load invoices.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInvoices();
  }, []);

  const sortedInvoices = useMemo(() => {
    return [...invoices].sort((a, b) => {
      const aDate = a?.invoiced_at ? new Date(a.invoiced_at).getTime() : 0;
      const bDate = b?.invoiced_at ? new Date(b.invoiced_at).getTime() : 0;
      if (bDate !== aDate) return bDate - aDate;
      return (b?.invoice_number || 0) - (a?.invoice_number || 0);
    });
  }, [invoices]);

  const closePreview = () => {
    setPreviewOpen(false);
    setPreviewLoading(false);
    setPreviewError("");
    setSendError("");
    setSendLoading(false);
    setActiveInvoice(null);
    setSendCustomer(true);
    setSendExpense(true);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl("");
    }
  };

  const openCreditMemo = async (invoice) => {
    setActiveInvoice(invoice);
    setPreviewOpen(true);
    setPreviewLoading(true);
    setPreviewError("");
    setSendError("");
    setSendCustomer(true);
    setSendExpense(true);
    try {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
        setPreviewUrl("");
      }
      const response = await fetch(`${apiBase()}/invoices/${invoice.invoice_number}/credit-memo/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!response.ok) {
        const contentType = response.headers.get("content-type") || "";
        const detail = contentType.includes("application/json") ? await response.json() : await response.text();
        const message = detail?.detail || detail || `Preview failed (${response.status})`;
        throw new Error(typeof message === "string" ? message : JSON.stringify(message));
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
      setPreviewUrl(url);
    } catch (err) {
      setPreviewError(err?.message || "Failed to load credit memo preview.");
    } finally {
      setPreviewLoading(false);
    }
  };

  const sendCreditMemo = async () => {
    if (!activeInvoice || (!sendCustomer && !sendExpense)) {
      return;
    }
    setSendLoading(true);
    setSendError("");
    try {
      await apiRequest(`/invoices/${activeInvoice.invoice_number}/credit-memo`, {
        method: "POST",
        body: JSON.stringify({
          send_customer: sendCustomer,
          send_expense: sendExpense,
        }),
      });
      closePreview();
      await loadInvoices();
    } catch (err) {
      setSendError(err?.message || "Failed to send credit memo.");
    } finally {
      setSendLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-serif text-3xl text-ink">Invoices</h1>
        <p className="text-sm text-ink/70">All generated invoices, newest first.</p>
      </header>
      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-ink">Invoice list</h2>
        <button className="btn-secondary" type="button" onClick={loadInvoices} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>
      <div className="overflow-x-auto rounded-2xl border border-sand/70 bg-white/80 shadow-soft">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-white/90 text-xs uppercase tracking-wide text-ink/60">
            <tr>
              <th className="px-4 py-3">Invoice #</th>
              <th className="px-4 py-3">Customer</th>
              <th className="px-4 py-3">Invoiced</th>
              <th className="px-4 py-3">Tasks</th>
              <th className="px-4 py-3">Total</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-sand/60">
            {sortedInvoices.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-center text-ink/60" colSpan={6}>
                  {loading ? "Loading invoices..." : "No invoices found."}
                </td>
              </tr>
            ) : (
              sortedInvoices.map((invoice) => (
                <tr key={invoice.invoice_number} className="hover:bg-white/70">
                  <td className="px-4 py-3 font-semibold text-ink">{invoice.invoice_number}</td>
                  <td className="px-4 py-3 text-ink/80">{invoice.customer_name || "Unknown"}</td>
                  <td className="px-4 py-3 text-ink/70">{formatDate(invoice.invoiced_at)}</td>
                  <td className="px-4 py-3 text-ink/70">{Number(invoice.task_count || 0).toLocaleString("da-DK")}</td>
                  <td className="px-4 py-3 text-ink/80">{formatCurrency(invoice.total_sum || 0)}</td>
                  <td className="px-4 py-3">
                    <button className="btn-secondary" type="button" onClick={() => openCreditMemo(invoice)}>
                      Create Credit Memo
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {previewOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
          <div className="w-full max-w-4xl rounded-2xl bg-white p-4 shadow-2xl">
            <div className="flex items-center justify-between gap-4 border-b border-sand/60 pb-3">
              <div>
                <h3 className="text-lg font-semibold text-ink">Credit memo preview</h3>
                <p className="text-xs text-ink/60">Invoice #{activeInvoice?.invoice_number}</p>
                <p className="text-xs text-ink/60">Customer: {activeInvoice?.customer_name || "Unknown"}</p>
              </div>
              <button className="btn-secondary" type="button" onClick={closePreview}>
                Close
              </button>
            </div>
            {previewError ? <p className="mt-3 text-sm text-red-700">{previewError}</p> : null}
            <div className="mt-4 h-[60vh] w-full overflow-hidden rounded-xl border border-sand/70 bg-sand/30">
              {previewUrl ? (
                <iframe className="h-full w-full" src={previewUrl} title="Credit memo preview" />
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-ink/60">
                  {previewLoading ? "Loading preview..." : "Preview unavailable."}
                </div>
              )}
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-4 text-sm text-ink/70">
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={sendCustomer} onChange={(event) => setSendCustomer(event.target.checked)} />
                  Send to customer
                </label>
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={sendExpense} onChange={(event) => setSendExpense(event.target.checked)} />
                  Send to {EXPENSE_EMAIL}
                </label>
              </div>
              <button
                className="btn"
                type="button"
                onClick={sendCreditMemo}
                disabled={sendLoading || (!sendCustomer && !sendExpense)}
              >
                {sendLoading ? "Sending..." : "Send credit memo"}
              </button>
            </div>
            {sendError ? <p className="mt-3 text-sm text-red-700">{sendError}</p> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
