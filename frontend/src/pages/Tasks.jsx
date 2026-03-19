import { useEffect, useState } from "react";
import { apiBase, apiRequest } from "../lib/api";

const initialForm = {
  customer_name: "",
  tasktype: "",
  pricing_type: "HourlyPrice",
  description: "",
  time_minutes: "",
  fixed_price: "",
  discount_percentage: "0",
  hourly_rate: "",
  invoice_status: "open",
};

export default function Tasks() {
  const [form, setForm] = useState(initialForm);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState([]);
  const [customersError, setCustomersError] = useState(null);
  const [customersLoading, setCustomersLoading] = useState(true);
  const [customerDirectory, setCustomerDirectory] = useState({});
  const [tasktypes, setTasktypes] = useState([]);
  const [tasktypesError, setTasktypesError] = useState(null);
  const [tasktypesLoading, setTasktypesLoading] = useState(true);
  const [tasks, setTasks] = useState([]);
  const [tasksError, setTasksError] = useState(null);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [filterCustomer, setFilterCustomer] = useState("");
  const [filterStart, setFilterStart] = useState("");
  const [filterEnd, setFilterEnd] = useState("");
  const [selectedTaskIds, setSelectedTaskIds] = useState([]);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [sendLoading, setSendLoading] = useState(false);
  const [sendError, setSendError] = useState(null);
  const [ccBookkeeping, setCcBookkeeping] = useState(false);
  const [pageSize, setPageSize] = useState(25);
  const [pageIndex, setPageIndex] = useState(1);
  const [showOnlyOpen, setShowOnlyOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const loadCustomers = async () => {
      setCustomersLoading(true);
      setCustomersError(null);
      try {
        const data = await apiRequest("/customers/full");
        if (!isMounted) {
          return;
        }
        const items = Array.isArray(data?.customers) ? data.customers : [];
        const names = items
          .map((item) => item.company_name || item.name || "")
          .filter(Boolean);
        const directory = items.reduce((acc, item) => {
          const key = item.company_name || item.name;
          if (key) {
            acc[key] = item;
          }
          return acc;
        }, {});
        setCustomers(names);
        setCustomerDirectory(directory);
      } catch (error) {
        if (!isMounted) {
          return;
        }
        setCustomersError(error.message);
        setCustomers([]);
        setCustomerDirectory({});
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

  useEffect(() => {
    let isMounted = true;
    const loadTasktypes = async () => {
      setTasktypesLoading(true);
      setTasktypesError(null);
      try {
        const data = await apiRequest("/tasktypes");
        if (!isMounted) {
          return;
        }
        const items = Array.isArray(data) ? data : data?.tasktypes;
        setTasktypes(Array.isArray(items) ? items : []);
      } catch (error) {
        if (!isMounted) {
          return;
        }
        setTasktypesError(error.message);
        setTasktypes([]);
      } finally {
        if (isMounted) {
          setTasktypesLoading(false);
        }
      }
    };
    loadTasktypes();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    const loadTasks = async () => {
      setTasksLoading(true);
      setTasksError(null);
      try {
        const data = await apiRequest("/tasks/full");
        if (!isMounted) {
          return;
        }
        setTasks(Array.isArray(data?.tasks) ? data.tasks : []);
      } catch (error) {
        if (!isMounted) {
          return;
        }
        setTasksError(error.message);
        setTasks([]);
      } finally {
        if (isMounted) {
          setTasksLoading(false);
        }
      }
    };
    loadTasks();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    setSelectedTaskIds([]);
    setPageIndex(1);
  }, [filterCustomer, filterStart, filterEnd]);

  useEffect(() => {
    setPageIndex(1);
  }, [pageSize]);

  const filteredTasks = showOnlyOpen ? tasks.filter((task) => !task.invoiced) : tasks;
  const sortedTasks = [...filteredTasks].sort((a, b) => {
    const dateA = a.date ? new Date(a.date).getTime() : 0;
    const dateB = b.date ? new Date(b.date).getTime() : 0;
    if (dateA !== dateB) {
      return dateB - dateA;
    }
    return (b.row_index || 0) - (a.row_index || 0);
  });

  const totalTasks = sortedTasks.length;
  const resolvedPageSize = pageSize === 0 ? totalTasks || 1 : pageSize;
  const totalPages = Math.max(1, Math.ceil(totalTasks / resolvedPageSize));
  const safePageIndex = Math.min(pageIndex, totalPages);
  const startOffset = (safePageIndex - 1) * resolvedPageSize;
  const endOffset = startOffset + resolvedPageSize;
  const visibleTasks = pageSize === 0 ? sortedTasks : sortedTasks.slice(startOffset, endOffset);

  const refreshTasks = async (useFilters = false) => {
    setTasksLoading(true);
    setTasksError(null);
    try {
      if (useFilters && filterCustomer) {
        const params = new URLSearchParams({ customer_name: filterCustomer });
        if (filterStart) {
          params.append("start_date", filterStart);
        }
        if (filterEnd) {
          params.append("end_date", filterEnd);
        }
        const data = await apiRequest(`/tasks/search?${params.toString()}`);
        setTasks(Array.isArray(data?.tasks) ? data.tasks : []);
      } else {
        const data = await apiRequest("/tasks/full");
        setTasks(Array.isArray(data?.tasks) ? data.tasks : []);
      }
      setSelectedTaskIds([]);
    } catch (error) {
      setTasksError(error.message);
      setTasks([]);
    } finally {
      setTasksLoading(false);
    }
  };

  const update = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setStatus(null);
    try {
      const payload = {
        customer_name: form.customer_name,
        tasktype: form.tasktype,
        pricing_type: form.pricing_type,
        description: form.description,
        discount_percentage: Number(form.discount_percentage || 0),
      };
      if (editingId) {
        payload.invoice_status = form.invoice_status;
      }
      if (form.pricing_type === "FixedPrice") {
        payload.fixed_price = Number(form.fixed_price || 0);
        if (form.time_minutes) {
          payload.time_minutes = Number(form.time_minutes || 0);
        }
      } else {
        payload.time_minutes = Number(form.time_minutes || 0);
        if (form.hourly_rate) {
          payload.hourly_rate = Number(form.hourly_rate || 0);
        }
      }
      const data = editingId
        ? await apiRequest(`/tasks/${editingId}`, {
            method: "PUT",
            body: JSON.stringify(payload),
          })
        : await apiRequest("/tasks", {
            method: "POST",
            body: JSON.stringify(payload),
          });
      setStatus({ ok: true, message: JSON.stringify(data, null, 2) });
      setForm(initialForm);
      setEditingId(null);
      await refreshTasks(Boolean(filterCustomer));
    } catch (error) {
      setStatus({ ok: false, message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (task) => {
    setEditingId(task.row_index);
    setForm({
      customer_name: task.customer_name || "",
      tasktype: task.tasktype || "",
      pricing_type: task.pricing_type || "HourlyPrice",
      description: task.description || "",
      time_minutes: task.time_minutes || "",
      fixed_price: task.pricing_type === "FixedPrice" ? task.price || "" : "",
      discount_percentage: task.discount_percentage ?? "0",
      hourly_rate: "",
      invoice_status: task.invoiced ? "invoiced" : "open",
    });
    setStatus(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm(initialForm);
  };

  const deleteTask = async (rowIndex) => {
    const confirmed = window.confirm("Delete this task?");
    if (!confirmed) {
      return;
    }
    setTasksError(null);
    try {
      await apiRequest(`/tasks/${rowIndex}`, { method: "DELETE" });
      if (editingId === rowIndex) {
        cancelEdit();
      }
      await refreshTasks(Boolean(filterCustomer));
    } catch (error) {
      setTasksError(error.message);
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

  const selectableTaskIds = visibleTasks.filter((task) => !task.invoiced).map((task) => task.row_index);

  const toggleAllTasks = () => {
    setSelectedTaskIds((prev) => {
      if (prev.length === selectableTaskIds.length) {
        return [];
      }
      return selectableTaskIds;
    });
  };

  const closePreview = () => {
    setPreviewOpen(false);
    setPreviewLoading(false);
    setPreviewError(null);
    setSendError(null);
    setCcBookkeeping(false);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
  };

  const selectedCustomerEmail = customerDirectory[filterCustomer]?.company_email || "";

  const previewInvoice = async () => {
    if (!filterCustomer || selectedTaskIds.length === 0) {
      return;
    }
    setPreviewOpen(true);
    setPreviewLoading(true);
    setPreviewError(null);
    setSendError(null);
    try {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
        setPreviewUrl(null);
      }
      const response = await fetch(`${apiBase()}/invoices/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_name: filterCustomer,
          start_date: filterStart || null,
          end_date: filterEnd || null,
          selected_task_ids: selectedTaskIds,
        }),
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
    } catch (error) {
      setPreviewError(error.message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const sendInvoice = async () => {
    if (!filterCustomer || selectedTaskIds.length === 0) {
      return;
    }
    setSendLoading(true);
    setSendError(null);
    try {
      const payload = {
        customer_name: filterCustomer,
        start_date: filterStart || null,
        end_date: filterEnd || null,
        send_email: true,
        cc_bookkeeping: ccBookkeeping,
        selected_task_ids: selectedTaskIds,
      };
      await apiRequest("/invoices", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      closePreview();
      setStatus({ ok: true, message: "Invoice sent." });
      await refreshTasks(Boolean(filterCustomer));
    } catch (error) {
      setSendError(error.message);
    } finally {
      setSendLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-serif text-3xl text-ink">Tasks</h1>
        <p className="text-sm text-ink/70">Log, edit, or remove billable tasks tied to customers.</p>
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
        <div className="space-y-2">
          <select
            className="input"
            value={form.tasktype}
            onChange={update("tasktype")}
            required
            disabled={tasktypesLoading}
          >
            <option value="">{tasktypesLoading ? "Loading task types..." : "Select task type"}</option>
            {tasktypes.map((tasktype) => (
              <option key={tasktype} value={tasktype}>
                {tasktype}
              </option>
            ))}
          </select>
          {tasktypesError ? <p className="text-xs text-red-700">{tasktypesError}</p> : null}
        </div>
        <select className="input" value={form.pricing_type} onChange={update("pricing_type")}> 
          <option value="HourlyPrice">Hourly price</option>
          <option value="FixedPrice">Fixed price</option>
        </select>
        {editingId ? (
          <select className="input" value={form.invoice_status} onChange={update("invoice_status")}>
            <option value="open">Invoice status: Open</option>
            <option value="invoiced">Invoice status: Invoiced</option>
          </select>
        ) : null}
        <input className="input" placeholder="Description" value={form.description} onChange={update("description")} required />
        {form.pricing_type === "FixedPrice" ? (
          <input className="input" placeholder="Fixed price" value={form.fixed_price} onChange={update("fixed_price")} />
        ) : (
          <input className="input" placeholder="Time in minutes" value={form.time_minutes} onChange={update("time_minutes")} required />
        )}
        {form.pricing_type === "FixedPrice" ? (
          <input className="input" placeholder="Time in minutes (optional)" value={form.time_minutes} onChange={update("time_minutes")} />
        ) : (
          <input className="input" placeholder="Hourly rate override (optional)" value={form.hourly_rate} onChange={update("hourly_rate")} />
        )}
        <input className="input" placeholder="Discount percentage" value={form.discount_percentage} onChange={update("discount_percentage")} />
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn" type="submit" disabled={loading}>
            {loading ? "Saving..." : editingId ? "Update task" : "Save task"}
          </button>
          {editingId ? (
            <button className="btn-secondary" type="button" onClick={cancelEdit}>
              Cancel edit
            </button>
          ) : null}
        </div>
      </form>
      {status ? (
        <pre className={`rounded-xl p-4 text-xs ${status.ok ? "bg-emerald-50 text-emerald-900" : "bg-red-50 text-red-700"}`}>
{status.message}
        </pre>
      ) : null}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-ink">All tasks</h2>
          <button className="btn-secondary" type="button" onClick={() => refreshTasks(Boolean(filterCustomer))} disabled={tasksLoading}>
            {tasksLoading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        <div className="grid gap-3 rounded-2xl border border-sand/70 bg-white/70 p-4 md:grid-cols-3">
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wide text-ink/60">Customer</label>
            <select
              className="input"
              value={filterCustomer}
              onChange={(event) => setFilterCustomer(event.target.value)}
              disabled={customersLoading}
            >
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
            <input
              className="input"
              type="date"
              value={filterStart}
              onChange={(event) => setFilterStart(event.target.value)}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wide text-ink/60">To date</label>
            <input
              className="input"
              type="date"
              value={filterEnd}
              onChange={(event) => setFilterEnd(event.target.value)}
            />
          </div>
          <div className="flex items-center gap-2 text-sm text-ink/70 md:col-span-3">
            <input
              type="checkbox"
              checked={showOnlyOpen}
              onChange={(event) => {
                setShowOnlyOpen(event.target.checked);
                setPageIndex(1);
              }}
            />
            <span>Show only open tasks</span>
          </div>
          <div className="flex flex-wrap items-center gap-2 md:col-span-3">
            <button className="btn" type="button" onClick={() => refreshTasks(true)} disabled={tasksLoading || !filterCustomer}>
              Apply filter
            </button>
            <button
              className="btn-secondary"
              type="button"
              onClick={() => {
                setFilterCustomer("");
                setFilterStart("");
                setFilterEnd("");
                setShowOnlyOpen(false);
                refreshTasks(false);
              }}
              disabled={tasksLoading}
            >
              Clear filter
            </button>
            {!filterCustomer ? <span className="text-xs text-ink/60">Select a customer to enable filtering.</span> : null}
          </div>
        </div>
        {tasksError ? (
          <pre className="rounded-xl bg-red-50 p-4 text-xs text-red-700">{tasksError}</pre>
        ) : null}
        <div className="overflow-x-auto rounded-2xl border border-sand/70 bg-white/80 shadow-soft">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-white/90 text-xs uppercase tracking-wide text-ink/60">
              <tr>
                <th className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selectedTaskIds.length > 0 && selectedTaskIds.length === selectableTaskIds.length}
                      onChange={toggleAllTasks}
                      disabled={selectableTaskIds.length === 0}
                    />
                    <span>Pick</span>
                  </div>
                </th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Task</th>
                <th className="px-4 py-3">Pricing</th>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">Discount</th>
                <th className="px-4 py-3">Sum</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sand/60">
              {visibleTasks.length === 0 ? (
                <tr>
                  <td className="px-4 py-6 text-center text-ink/60" colSpan={11}>
                    {tasksLoading ? "Loading tasks..." : "No tasks found."}
                  </td>
                </tr>
              ) : (
                visibleTasks.map((task) => (
                  <tr key={task.row_index} className="hover:bg-white/70">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedTaskIds.includes(task.row_index)}
                        onChange={() => toggleTask(task.row_index)}
                        disabled={task.invoiced}
                      />
                    </td>
                    <td className="px-4 py-3 text-ink/80">{task.date}</td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-ink">{task.customer_name}</div>
                      <div className="text-xs text-ink/60">{task.tasktype}</div>
                    </td>
                    <td className="px-4 py-3 text-ink/80">{task.description}</td>
                    <td className="px-4 py-3 text-ink/80">{task.pricing_type}</td>
                    <td className="px-4 py-3 text-ink/80">{task.time_minutes || "-"}</td>
                    <td className="px-4 py-3 text-ink/80">{task.price}</td>
                    <td className="px-4 py-3 text-ink/80">{task.discount_percentage || "0"}%</td>
                    <td className="px-4 py-3 text-ink/80">{task.sum}</td>
                    <td className="px-4 py-3">
                      {task.invoiced ? (
                        <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                          Invoiced
                        </span>
                      ) : (
                        <span className="rounded-full bg-sand/60 px-3 py-1 text-xs font-semibold text-ink/60">
                          Open
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button className="btn-secondary" type="button" onClick={() => startEdit(task)}>
                          Edit
                        </button>
                        <button className="btn" type="button" onClick={() => deleteTask(task.row_index)}>
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
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3 text-xs text-ink/60">
            <p>Selected tasks: {selectedTaskIds.length}</p>
            <p>
              Showing {totalTasks === 0 ? 0 : startOffset + 1}-{Math.min(endOffset, totalTasks)} of {totalTasks}
            </p>
          </div>
          <button className="btn" type="button" onClick={previewInvoice} disabled={previewLoading || !filterCustomer || selectedTaskIds.length === 0}>
            {previewLoading ? "Generating preview..." : "Preview invoice"}
          </button>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-sand/70 bg-white/70 p-3">
          <div className="flex items-center gap-2 text-sm text-ink/70">
            <label>Tasks per page</label>
            <select
              className="input"
              value={String(pageSize)}
              onChange={(event) => setPageSize(Number(event.target.value))}
            >
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="0">All</option>
            </select>
          </div>
          <div className="flex items-center gap-2 text-sm text-ink/70">
            <button
              className="btn-secondary"
              type="button"
              onClick={() => setPageIndex((prev) => Math.max(1, prev - 1))}
              disabled={safePageIndex <= 1 || pageSize === 0}
            >
              Previous
            </button>
            <span>
              Page {safePageIndex} of {totalPages}
            </span>
            <button
              className="btn-secondary"
              type="button"
              onClick={() => setPageIndex((prev) => Math.min(totalPages, prev + 1))}
              disabled={safePageIndex >= totalPages || pageSize === 0}
            >
              Next
            </button>
          </div>
        </div>
        {previewError ? <p className="text-sm text-red-700">{previewError}</p> : null}
      </section>
      {previewOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
          <div className="w-full max-w-4xl rounded-2xl bg-white p-4 shadow-2xl">
            <div className="flex items-center justify-between gap-4 border-b border-sand/60 pb-3">
              <div>
                <h3 className="text-lg font-semibold text-ink">Invoice preview</h3>
                <p className="text-xs text-ink/60">Customer: {filterCustomer}</p>
                <p className="text-xs text-ink/60">
                  Recipient: {selectedCustomerEmail || "Missing email in Kunder sheet"}
                </p>
              </div>
              <button className="btn-secondary" type="button" onClick={closePreview}>
                Close
              </button>
            </div>
            {previewError ? <p className="mt-3 text-sm text-red-700">{previewError}</p> : null}
            <div className="mt-4 h-[60vh] w-full overflow-hidden rounded-xl border border-sand/70 bg-sand/30">
              {previewUrl ? (
                <iframe className="h-full w-full" src={previewUrl} title="Invoice preview" />
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-ink/60">Loading preview...</div>
              )}
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <label className="flex items-center gap-2 text-sm text-ink/70">
                <input type="checkbox" checked={ccBookkeeping} onChange={(event) => setCcBookkeeping(event.target.checked)} />
                CC bookkeeping (341bilag2401129@e-conomic.dk)
              </label>
              <button className="btn" type="button" onClick={sendInvoice} disabled={sendLoading}>
                {sendLoading ? "Sending..." : "Send invoice"}
              </button>
            </div>
            {sendError ? <p className="mt-3 text-sm text-red-700">{sendError}</p> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
