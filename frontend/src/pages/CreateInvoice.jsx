import { useEffect, useRef, useState } from "react";
import { apiBase, apiRequest } from "../lib/api";

const initialForm = {
  customer_name: "",
  start_date: "",
  end_date: "",
  send_email: true,
  cc_emails: "",
  cc_bookkeeping: false,
  allow_reinvoice: false,
};

const initialCreditForm = {
  customer_name: "",
  description: "",
  net_amount: "",
  original_invoice_number: "",
  customer_email_override: "",
  send_customer: true,
  cc_bookkeeping: true,
};

function formatCurrency(value) {
  return new Intl.NumberFormat("da-DK", {
    style: "currency",
    currency: "DKK",
    maximumFractionDigits: 2,
  }).format(value || 0);
}

export default function CreateInvoice() {
  const [form, setForm] = useState(initialForm);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState([]);
  const [customersError, setCustomersError] = useState(null);
  const [customersLoading, setCustomersLoading] = useState(true);
  const [tasks, setTasks] = useState([]);
  const [tasksError, setTasksError] = useState(null);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [selectedTaskIds, setSelectedTaskIds] = useState([]);
  const [creditForm, setCreditForm] = useState(initialCreditForm);
  const [creditStatus, setCreditStatus] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewSeen, setPreviewSeen] = useState(false);
  const [creditSending, setCreditSending] = useState(false);
  const [creditSendError, setCreditSendError] = useState("");
  const previewUrlRef = useRef("");

  useEffect(() => {
    let isMounted = true;
    const loadCustomers = async () => {
      setCustomersLoading(true);
      setCustomersError(null);
      try {
        const data = await apiRequest("/customers");
        if (!isMounted) {
          return;
        }
        const names = Array.isArray(data) ? data : data?.customers;
        setCustomers(Array.isArray(names) ? names : []);
      } catch (error) {
        if (!isMounted) {
          return;
        }
        setCustomersError(error.message);
        setCustomers([]);
      } finally {
        if (isMounted) {
          setCustomersLoading(false);
        }
      }
    };
    loadCustomers();
    return () => {
      isMounted = false;
    };
  }, []);

  const update = (field) => (event) => {
    const value = event.target.type === "checkbox" ? event.target.checked : event.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const searchTasks = async () => {
    setTasksLoading(true);
    setTasksError(null);
    setTasks([]);
    setSelectedTaskIds([]);
    try {
      const params = new URLSearchParams({
        customer_name: form.customer_name,
      });
      if (form.start_date) {
        params.set("start_date", form.start_date);
      }
      if (form.end_date) {
        params.set("end_date", form.end_date);
      }
      const data = await apiRequest(`/tasks/search?${params.toString()}`);
      const items = data?.tasks || [];
      setTasks(items);
    } catch (error) {
      setTasksError(error.message);
    } finally {
      setTasksLoading(false);
    }
  };

  const toggleTask = (taskId) => {
    setSelectedTaskIds((prev) => {
      if (prev.includes(taskId)) {
        return prev.filter((id) => id !== taskId);
      }
      return [...prev, taskId];
    });
  };

  const toggleAllTasks = () => {
    if (selectedTaskIds.length === tasks.length) {
      setSelectedTaskIds([]);
    } else {
      setSelectedTaskIds(tasks.map((task) => task.row_index));
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setStatus(null);
    try {
      const payload = {
        customer_name: form.customer_name,
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        send_email: Boolean(form.send_email),
        cc_bookkeeping: Boolean(form.cc_bookkeeping),
        allow_reinvoice: Boolean(form.allow_reinvoice),
        selected_task_ids: selectedTaskIds,
      };
      if (form.cc_emails.trim()) {
        payload.cc_emails = form.cc_emails.split(",").map((email) => email.trim()).filter(Boolean);
      }
      const data = await apiRequest("/invoices", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setStatus({ ok: true, message: JSON.stringify(data, null, 2) });
      setForm(initialForm);
      setTasks([]);
      setSelectedTaskIds([]);
    } catch (error) {
      setStatus({ ok: false, message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const updateCredit = (field) => (event) => {
    const value = event.target.type === "checkbox" ? event.target.checked : event.target.value;
    setCreditForm((prev) => ({ ...prev, [field]: value }));
  };

  const netAmount = parseFloat(creditForm.net_amount) || 0;
  const vatAmount = Math.round(netAmount * 0.25 * 100) / 100;
  const grossAmount = Math.round((netAmount + vatAmount) * 100) / 100;
  const creditValid =
    creditForm.customer_name.trim() !== "" &&
    creditForm.description.trim() !== "" &&
    netAmount > 0;

  const closeCreditPreview = () => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = "";
    }
    setPreviewUrl("");
    setPreviewError("");
    setCreditSendError("");
    setPreviewOpen(false);
  };

  const previewCreditMemo = async () => {
    if (!creditValid) return;
    setPreviewOpen(true);
    setPreviewLoading(true);
    setPreviewError("");
    setPreviewSeen(false);
    try {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = "";
      }
      setPreviewUrl("");
      const response = await fetch(`${apiBase()}/credit-memos/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_name: creditForm.customer_name,
          description: creditForm.description,
          net_amount: netAmount,
          original_invoice_number: creditForm.original_invoice_number || null,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data?.detail || `Preview failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      previewUrlRef.current = url;
      setPreviewUrl(url);
      setPreviewSeen(true);
    } catch (error) {
      setPreviewError(error?.message || "Failed to load preview.");
    } finally {
      setPreviewLoading(false);
    }
  };

  const sendCreditMemo = async () => {
    if (!previewSeen || previewError) return;
    setCreditSending(true);
    setCreditSendError("");
    try {
      const payload = {
        customer_name: creditForm.customer_name,
        description: creditForm.description,
        net_amount: netAmount,
        original_invoice_number: creditForm.original_invoice_number || null,
        customer_email_override: creditForm.customer_email_override || null,
        send_customer: Boolean(creditForm.send_customer),
        cc_bookkeeping: Boolean(creditForm.cc_bookkeeping),
      };
      const data = await apiRequest("/credit-memos", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      closeCreditPreview();
      setCreditForm(initialCreditForm);
      setCreditStatus({ ok: true, message: JSON.stringify(data, null, 2) });
    } catch (error) {
      setCreditSendError(error?.message || "Failed to create credit memo.");
    } finally {
      setCreditSending(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-serif text-3xl text-ink">Create invoice</h1>
        <p className="text-sm text-ink/70">Generate a PDF invoice and send it by email.</p>
      </header>
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <select
            className="input"
            value={form.customer_name}
            onChange={update("customer_name")}
            required
            disabled={customersLoading}
          >
            <option value="">{customersLoading ? "Loading customers..." : "Select customer"}</option>
            {customers.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          {customersError ? <p className="text-xs text-red-700">{customersError}</p> : null}
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-ink/70">Send email</label>
          <input type="checkbox" checked={form.send_email} onChange={update("send_email")} />
        </div>
        <input className="input" type="date" placeholder="Start date" value={form.start_date} onChange={update("start_date")} />
        <input className="input" type="date" placeholder="End date" value={form.end_date} onChange={update("end_date")} />
        <button className="btn" type="button" onClick={searchTasks} disabled={tasksLoading || !form.customer_name}>
          {tasksLoading ? "Searching tasks..." : "Search for tasks"}
        </button>
        <input className="input" placeholder="CC emails (comma separated)" value={form.cc_emails} onChange={update("cc_emails")} />
        <div className="flex items-center gap-2">
          <label className="text-sm text-ink/70">CC bookkeeping (341bilag2401129@e-conomic.dk)</label>
          <input type="checkbox" checked={form.cc_bookkeeping} onChange={update("cc_bookkeeping")} />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-ink/70">Allow reinvoice</label>
          <input type="checkbox" checked={form.allow_reinvoice} onChange={update("allow_reinvoice")} />
        </div>
        <button className="btn" type="submit" disabled={loading || selectedTaskIds.length === 0}>
          {loading ? "Sending..." : "Send invoice"}
        </button>
      </form>
      {tasksError ? <p className="text-sm text-red-700">{tasksError}</p> : null}
      {tasks.length > 0 ? (
        <div className="rounded-2xl border border-sand/70 bg-white/70 p-4 shadow-soft">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-serif text-xl text-ink">Tasks</h2>
            <button className="btn" type="button" onClick={toggleAllTasks}>
              {selectedTaskIds.length === tasks.length ? "Clear selection" : "Select all"}
            </button>
          </div>
          <div className="mt-4 overflow-auto">
            <table className="min-w-full text-xs text-ink/80">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-[0.3em] text-ink/50">
                  <th className="py-2">Pick</th>
                  <th className="py-2">Date</th>
                  <th className="py-2">Task type</th>
                  <th className="py-2">Description</th>
                  <th className="py-2">Minutes</th>
                  <th className="py-2">Price</th>
                  <th className="py-2">Discount</th>
                  <th className="py-2">Sum</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.row_index} className="border-t border-sand/60">
                    <td className="py-2">
                      <input type="checkbox" checked={selectedTaskIds.includes(task.row_index)} onChange={() => toggleTask(task.row_index)} />
                    </td>
                    <td className="py-2">{task.date}</td>
                    <td className="py-2">{task.tasktype}</td>
                    <td className="py-2">{task.description}</td>
                    <td className="py-2">{task.time_minutes}</td>
                    <td className="py-2">{task.price}</td>
                    <td className="py-2">{task.discount_percentage}</td>
                    <td className="py-2">{task.sum}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
      {status ? (
        <pre className={`rounded-xl p-4 text-xs ${status.ok ? "bg-emerald-50 text-emerald-900" : "bg-red-50 text-red-700"}`}>
{status.message}
        </pre>
      ) : null}

      <section className="rounded-2xl border border-sand/70 bg-white/70 p-5 shadow-soft">
        <div className="mb-3">
          <h2 className="font-serif text-2xl text-ink">Create credit memo</h2>
          <p className="text-sm text-ink/70">
            Enter net amount (excl. 25% VAT). Total incl. VAT is calculated automatically.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1 md:col-span-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-ink/60">Customer *</label>
            <select className="input" value={creditForm.customer_name} onChange={updateCredit("customer_name")}>
              <option value="">Select customer</option>
              {customers.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1 md:col-span-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-ink/60">Description *</label>
            <textarea
              className="input min-h-[84px] resize-y"
              value={creditForm.description}
              onChange={updateCredit("description")}
              placeholder="Describe why this credit memo is issued"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wide text-ink/60">Amount ex. VAT (DKK) *</label>
            <input
              className="input"
              type="number"
              step="0.01"
              min="0.01"
              value={creditForm.net_amount}
              onChange={updateCredit("net_amount")}
              placeholder="0.00"
            />
          </div>
          <div className="rounded-xl bg-sand/30 p-3 text-sm text-ink/80 space-y-1">
            <div className="flex justify-between"><span>Net:</span><span>{formatCurrency(netAmount)}</span></div>
            <div className="flex justify-between"><span>VAT 25%:</span><span>{formatCurrency(vatAmount)}</span></div>
            <div className="flex justify-between border-t border-sand/70 pt-1 font-semibold"><span>Total incl. VAT:</span><span>{formatCurrency(grossAmount)}</span></div>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wide text-ink/60">Original invoice no. (optional)</label>
            <input className="input" value={creditForm.original_invoice_number} onChange={updateCredit("original_invoice_number")} />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wide text-ink/60">Customer email override</label>
            <input className="input" type="email" value={creditForm.customer_email_override} onChange={updateCredit("customer_email_override")} placeholder="optional" />
          </div>
          <label className="flex items-center gap-2 text-sm text-ink/80">
            <input type="checkbox" checked={creditForm.send_customer} onChange={updateCredit("send_customer")} />
            Send to customer
          </label>
          <label className="flex items-center gap-2 text-sm text-ink/80">
            <input type="checkbox" checked={creditForm.cc_bookkeeping} onChange={updateCredit("cc_bookkeeping")} />
            CC bookkeeping
          </label>
          <div className="md:col-span-2">
            <button className="btn" type="button" onClick={previewCreditMemo} disabled={!creditValid || previewLoading}>
              {previewLoading ? "Generating preview..." : "Preview credit memo"}
            </button>
            {!creditValid ? <p className="mt-1 text-xs text-ink/50">Fill all required fields to preview.</p> : null}
          </div>
        </div>
      </section>

      {creditStatus ? (
        <pre className={`rounded-xl p-4 text-xs ${creditStatus.ok ? "bg-emerald-50 text-emerald-900" : "bg-red-50 text-red-700"}`}>
{creditStatus.message}
        </pre>
      ) : null}

      {previewOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-sm">
          <div className="flex h-[90vh] w-full max-w-5xl flex-col rounded-3xl border border-sand/70 bg-white shadow-soft">
            <div className="flex items-center justify-between border-b border-sand/70 px-6 py-4">
              <h3 className="text-lg font-semibold text-ink">Credit memo preview</h3>
              <button type="button" onClick={closeCreditPreview} className="text-xl leading-none text-ink/50 hover:text-ink">&times;</button>
            </div>
            <div className="flex-1 overflow-hidden p-4">
              {previewError ? <p className="text-sm text-red-700">{previewError}</p> : null}
              {!previewError && previewUrl ? (
                <iframe className="h-full w-full" src={previewUrl} title="Credit memo preview" />
              ) : null}
              {!previewError && !previewUrl ? (
                <div className="flex h-full items-center justify-center text-sm text-ink/60">
                  {previewLoading ? "Loading preview..." : "Preview unavailable."}
                </div>
              ) : null}
            </div>
            <div className="flex flex-col gap-2 border-t border-sand/70 px-6 py-4">
              {creditSendError ? <p className="text-sm text-red-700">{creditSendError}</p> : null}
              <div className="flex justify-end gap-3">
                <button type="button" className="btn-secondary" onClick={closeCreditPreview}>Cancel</button>
                <button type="button" className="btn" onClick={sendCreditMemo} disabled={!previewSeen || previewLoading || creditSending || Boolean(previewError)}>
                  {creditSending ? "Sending..." : "Send credit memo"}
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
