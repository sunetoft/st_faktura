import { useEffect, useState } from "react";
import { apiRequest } from "../lib/api";

const initialForm = {
  customer_name: "",
  start_date: "",
  end_date: "",
  send_email: true,
  cc_emails: "",
  cc_bookkeeping: false,
  allow_reinvoice: false,
};

export default function Invoices() {
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
          <label className="text-sm text-ink/70">CC bookkeeping (indtaegt@ebogholderen.dk)</label>
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
    </div>
  );
}
