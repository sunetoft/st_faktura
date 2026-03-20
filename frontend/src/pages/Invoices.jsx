import { useEffect, useMemo, useState } from "react";
import { apiBase, apiRequest } from "../lib/api";

const EXPENSE_EMAIL = "udgift@ebogholderen.dk";

const SORTABLE_COLUMNS = ["type", "customer_name", "document_number", "document_date", "total_amount"];

async function tryApiPaths(paths, options) {
  let lastError = null;
  for (const path of paths) {
    try {
      // Try candidates in order and stop on first success.
      // eslint-disable-next-line no-await-in-loop
      const data = await apiRequest(path, options);
      return { data, path };
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error("All endpoint candidates failed.");
}

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
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");
  const [apiCapabilities, setApiCapabilities] = useState({
    creditMemoListPath: "",
    creditMemoDeletePath: "",
    invoiceDeletePath: "",
  });
  const [filterCustomer, setFilterCustomer] = useState("");
  const [filterStart, setFilterStart] = useState("");
  const [filterEnd, setFilterEnd] = useState("");
  const [sortBy, setSortBy] = useState("document_date");
  const [sortDirection, setSortDirection] = useState("desc");

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [sendLoading, setSendLoading] = useState(false);
  const [sendError, setSendError] = useState("");
  const [sendCustomer, setSendCustomer] = useState(true);
  const [sendExpense, setSendExpense] = useState(true);
  const [activeInvoice, setActiveInvoice] = useState(null);

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const loadInvoices = async () => {
    setLoading(true);
    setError("");
    setWarning("");
    try {
      const invoiceData = await apiRequest("/invoices/list");
      const invoiceRows = (Array.isArray(invoiceData?.invoices) ? invoiceData.invoices : []).map((item) => ({
        ...item,
        type: "invoice",
        document_number: item?.invoice_number ?? 0,
        document_date: item?.invoiced_at || item?.invoice_date || "",
        customer_name: item?.customer_name || "",
      }));

      let creditMemoRows = [];
      try {
        const creditResult = await tryApiPaths([
          "/credit-memos/list",
          "/credit_memos/list",
          "/credit-memos",
          "/credit_memos",
        ]);
        const creditData = creditResult.data;
        setApiCapabilities((prev) => ({ ...prev, creditMemoListPath: creditResult.path }));
        const rawCreditMemos = Array.isArray(creditData?.credit_memos)
          ? creditData.credit_memos
          : Array.isArray(creditData?.creditMemos)
            ? creditData.creditMemos
            : [];
        creditMemoRows = rawCreditMemos.map((item) => ({
          ...item,
          type: "credit_memo",
          document_number: item?.credit_memo_number ?? item?.invoice_number ?? 0,
          document_date: item?.created_at || item?.credit_memo_date || "",
          customer_name: item?.customer_name || "",
        }));
      } catch {
        setWarning("Credit memo list endpoint is unavailable. Showing invoices only.");
      }

      setDocuments([...invoiceRows, ...creditMemoRows]);
    } catch (err) {
      setError(err?.message || "Failed to load invoices.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInvoices();
  }, []);

  const customers = useMemo(() => {
    const names = new Set();
    documents.forEach((doc) => {
      if (doc?.customer_name) {
        names.add(doc.customer_name);
      }
    });
    return Array.from(names).sort((a, b) => a.localeCompare(b, "da"));
  }, [documents]);

  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      const customerOk = !filterCustomer || (doc?.customer_name || "") === filterCustomer;
      const docDate = doc?.document_date ? new Date(doc.document_date) : null;
      const docTime = docDate && !Number.isNaN(docDate.getTime()) ? docDate.getTime() : null;

      const fromTime = filterStart ? new Date(`${filterStart}T00:00:00`).getTime() : null;
      const toTime = filterEnd ? new Date(`${filterEnd}T23:59:59`).getTime() : null;

      const dateFromOk = fromTime == null || (docTime != null && docTime >= fromTime);
      const dateToOk = toTime == null || (docTime != null && docTime <= toTime);
      return customerOk && dateFromOk && dateToOk;
    });
  }, [documents, filterCustomer, filterStart, filterEnd]);

  const sortedDocuments = useMemo(() => {
    const factor = sortDirection === "asc" ? 1 : -1;
    const sorted = [...filteredDocuments].sort((a, b) => {
      const getDate = (row) => {
        const parsed = row?.document_date ? new Date(row.document_date).getTime() : 0;
        return Number.isNaN(parsed) ? 0 : parsed;
      };

      if (sortBy === "document_date") {
        const delta = getDate(a) - getDate(b);
        if (delta !== 0) return delta * factor;
        return ((a?.document_number || 0) - (b?.document_number || 0)) * factor;
      }
      if (sortBy === "document_number") {
        const delta = (a?.document_number || 0) - (b?.document_number || 0);
        if (delta !== 0) return delta * factor;
        return (getDate(a) - getDate(b)) * factor;
      }
      if (sortBy === "customer_name") {
        const delta = (a?.customer_name || "").localeCompare(b?.customer_name || "", "da");
        if (delta !== 0) return delta * factor;
        return ((a?.document_number || 0) - (b?.document_number || 0)) * factor;
      }
      if (sortBy === "type") {
        const delta = (a?.type || "").localeCompare(b?.type || "", "da");
        if (delta !== 0) return delta * factor;
        return ((a?.document_number || 0) - (b?.document_number || 0)) * factor;
      }
      if (sortBy === "total_amount") {
        const amountA = Number(a?.total_sum ?? a?.amount_incl_vat ?? 0);
        const amountB = Number(b?.total_sum ?? b?.amount_incl_vat ?? 0);
        const delta = amountA - amountB;
        if (delta !== 0) return delta * factor;
        return ((a?.document_number || 0) - (b?.document_number || 0)) * factor;
      }
      return 0;
    });
    return sorted;
  }, [filteredDocuments, sortBy, sortDirection]);

  const setSort = (column) => {
    if (!SORTABLE_COLUMNS.includes(column)) {
      return;
    }
    if (sortBy === column) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
      return;
    }
    setSortBy(column);
    setSortDirection(column === "document_date" ? "desc" : "asc");
  };

  const sortIndicator = (column) => {
    if (sortBy !== column) {
      return "";
    }
    return sortDirection === "asc" ? " ▲" : " ▼";
  };

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

  const closeDelete = () => {
    setDeleteOpen(false);
    setDeleteTarget(null);
    setDeleteConfirm("");
    setDeleteLoading(false);
    setDeleteError("");
  };

  const openDelete = (doc) => {
    setDeleteTarget(doc);
    setDeleteOpen(true);
    setDeleteConfirm("");
    setDeleteError("");
  };

  const deleteDocument = async () => {
    if (!deleteTarget) {
      return;
    }
    const expected = "DELETE";
    if (deleteConfirm.trim().toUpperCase() !== expected) {
      setDeleteError("Type DELETE to confirm removal.");
      return;
    }

    setDeleteLoading(true);
    setDeleteError("");
    try {
      if (deleteTarget.type === "credit_memo") {
        const result = await tryApiPaths(
          [
            `/credit-memos/${deleteTarget.document_number}?delete_drive=true`,
            `/credit_memos/${deleteTarget.document_number}?delete_drive=true`,
            `/credit-memos/${deleteTarget.document_number}`,
            `/credit_memos/${deleteTarget.document_number}`,
          ],
          { method: "DELETE" }
        );
        setApiCapabilities((prev) => ({ ...prev, creditMemoDeletePath: result.path }));
      } else {
        const result = await tryApiPaths(
          [
            `/invoices/${deleteTarget.document_number}?delete_drive=true`,
            `/invoices/${deleteTarget.document_number}`,
          ],
          { method: "DELETE" }
        );
        setApiCapabilities((prev) => ({ ...prev, invoiceDeletePath: result.path }));
      }
      closeDelete();
      await loadInvoices();
    } catch (err) {
      setDeleteError(err?.message || "Failed to delete document.");
    } finally {
      setDeleteLoading(false);
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
        <p className="text-sm text-ink/70">All invoices and credit memos with filtering, sorting, and admin actions.</p>
      </header>
      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
      {warning ? <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{warning}</div> : null}
      <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-xs text-sky-900">
        <p className="font-semibold">API capability status</p>
        <p>Credit memo list endpoint: {apiCapabilities.creditMemoListPath || "not detected yet"}</p>
        <p>Credit memo delete endpoint: {apiCapabilities.creditMemoDeletePath || "not detected yet"}</p>
        <p>Invoice delete endpoint: {apiCapabilities.invoiceDeletePath || "not detected yet"}</p>
      </div>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-ink">Document list</h2>
        <button className="btn-secondary" type="button" onClick={loadInvoices} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div className="grid gap-3 rounded-2xl border border-sand/70 bg-white/70 p-4 md:grid-cols-3">
        <div className="space-y-1">
          <label className="text-xs font-semibold uppercase tracking-wide text-ink/60">Customer</label>
          <select className="input" value={filterCustomer} onChange={(event) => setFilterCustomer(event.target.value)}>
            <option value="">All customers</option>
            {customers.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold uppercase tracking-wide text-ink/60">From date</label>
          <input className="input" type="date" value={filterStart} onChange={(event) => setFilterStart(event.target.value)} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold uppercase tracking-wide text-ink/60">To date</label>
          <input className="input" type="date" value={filterEnd} onChange={(event) => setFilterEnd(event.target.value)} />
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-sand/70 bg-white/80 shadow-soft">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-white/90 text-xs uppercase tracking-wide text-ink/60">
            <tr>
              <th className="px-4 py-3">
                <button className="font-semibold" type="button" onClick={() => setSort("type")}>Type{sortIndicator("type")}</button>
              </th>
              <th className="px-4 py-3">
                <button className="font-semibold" type="button" onClick={() => setSort("customer_name")}>Customer{sortIndicator("customer_name")}</button>
              </th>
              <th className="px-4 py-3">
                <button className="font-semibold" type="button" onClick={() => setSort("document_number")}>Number{sortIndicator("document_number")}</button>
              </th>
              <th className="px-4 py-3">
                <button className="font-semibold" type="button" onClick={() => setSort("document_date")}>Date{sortIndicator("document_date")}</button>
              </th>
              <th className="px-4 py-3">
                <button className="font-semibold" type="button" onClick={() => setSort("total_amount")}>Total{sortIndicator("total_amount")}</button>
              </th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-sand/60">
            {sortedDocuments.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-center text-ink/60" colSpan={6}>
                  {loading ? "Loading documents..." : "No documents found."}
                </td>
              </tr>
            ) : (
              sortedDocuments.map((doc) => (
                <tr key={`${doc.type}-${doc.document_number}`} className="hover:bg-white/70">
                  <td className="px-4 py-3 text-ink/80">{doc.type === "credit_memo" ? "Credit memo" : "Invoice"}</td>
                  <td className="px-4 py-3 text-ink/80">{doc.customer_name || "Unknown"}</td>
                  <td className="px-4 py-3 font-semibold text-ink">{doc.document_number}</td>
                  <td className="px-4 py-3 text-ink/70">{formatDate(doc.document_date)}</td>
                  <td className="px-4 py-3 text-ink/80">{formatCurrency(doc.total_sum || doc.amount_incl_vat || 0)}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {doc.type !== "credit_memo" ? (
                        <button className="btn-secondary" type="button" onClick={() => openCreditMemo(doc)}>
                          Revert to Credit Memo
                        </button>
                      ) : null}
                      <button className="btn-secondary" type="button" onClick={() => openDelete(doc)}>
                        Delete
                      </button>
                    </div>
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

      {deleteOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-2xl">
            <h3 className="text-lg font-semibold text-ink">Delete document</h3>
            <p className="mt-2 text-sm text-ink/70">
              This will permanently delete the selected {deleteTarget?.type === "credit_memo" ? "credit memo" : "invoice"} and request deletion of its PDF on Google Drive.
            </p>
            <p className="mt-2 text-sm text-ink/70">
              Customer: {deleteTarget?.customer_name || "Unknown"} | Number: {deleteTarget?.document_number || "-"}
            </p>
            <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-ink/60">Type DELETE to confirm</label>
            <input
              className="input mt-1"
              value={deleteConfirm}
              onChange={(event) => setDeleteConfirm(event.target.value)}
              placeholder="DELETE"
            />
            {deleteError ? <p className="mt-2 text-sm text-red-700">{deleteError}</p> : null}
            <div className="mt-4 flex items-center justify-end gap-2">
              <button className="btn-secondary" type="button" onClick={closeDelete} disabled={deleteLoading}>
                Cancel
              </button>
              <button className="btn" type="button" onClick={deleteDocument} disabled={deleteLoading}>
                {deleteLoading ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
