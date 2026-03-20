import { useEffect, useMemo, useState } from "react";
import { apiBase, apiRequest } from "../lib/api";

function StatWidget({ title, description, children }) {
  return (
    <section className="rounded-2xl border border-sand/70 bg-white/80 p-6 shadow-soft">
      <header className="space-y-1">
        <h3 className="font-serif text-2xl text-ink">{title}</h3>
        <p className="text-sm text-ink/60">{description}</p>
      </header>
      <div className="mt-5 space-y-4">{children}</div>
    </section>
  );
}

function toDateInputValue(date) {
  if (!date) return "";
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getQuarterRange(now = new Date()) {
  const quarterStartMonth = Math.floor(now.getMonth() / 3) * 3;
  const start = new Date(now.getFullYear(), quarterStartMonth, 1);
  return {
    start: toDateInputValue(start),
    end: toDateInputValue(now),
    label: `Q${Math.floor(now.getMonth() / 3) + 1} ${now.getFullYear()}`,
  };
}

function getLastQuarterRange(now = new Date()) {
  const currentQuarterStart = Math.floor(now.getMonth() / 3) * 3;
  let year = now.getFullYear();
  let lastQuarterStartMonth = currentQuarterStart - 3;
  if (lastQuarterStartMonth < 0) {
    lastQuarterStartMonth += 12;
    year -= 1;
  }
  const start = new Date(year, lastQuarterStartMonth, 1);
  const end = new Date(now.getFullYear(), currentQuarterStart, 0);
  const labelQuarter = Math.floor(lastQuarterStartMonth / 3) + 1;
  return {
    start: toDateInputValue(start),
    end: toDateInputValue(end),
    label: `Q${labelQuarter} ${year}`,
  };
}

function getYearToDateRange(now = new Date()) {
  const start = new Date(now.getFullYear(), 0, 1);
  return {
    start: toDateInputValue(start),
    end: toDateInputValue(now),
    label: `YTD ${now.getFullYear()}`,
  };
}

function getRangePresets(now = new Date()) {
  const currentQuarter = getQuarterRange(now);
  const lastQuarter = getLastQuarterRange(now);
  const ytd = getYearToDateRange(now);
  return [
    {
      id: "this-quarter",
      label: "This quarter",
      detail: currentQuarter.label,
      ...currentQuarter,
    },
    {
      id: "last-quarter",
      label: "Last quarter",
      detail: lastQuarter.label,
      ...lastQuarter,
    },
    {
      id: "ytd",
      label: "Year to date",
      detail: ytd.label,
      ...ytd,
    },
  ];
}

function parseTaskDate(value) {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed;
}

function isWithinRange(dateValue, startValue, endValue) {
  const taskDate = parseTaskDate(dateValue);
  if (!taskDate) return false;
  const startDate = startValue ? parseTaskDate(startValue) : null;
  const endDate = endValue ? parseTaskDate(endValue) : null;
  if (startDate && taskDate < startDate) return false;
  if (endDate && taskDate > endDate) return false;
  return true;
}

function parseAmount(value) {
  if (value === null || value === undefined) return 0;
  if (typeof value === "number") return value;
  const normalized = `${value}`.replace(",", ".").trim();
  const parsed = Number.parseFloat(normalized);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function formatCurrency(value) {
  return new Intl.NumberFormat("da-DK", {
    style: "currency",
    currency: "DKK",
    maximumFractionDigits: 2,
  }).format(value);
}

export default function Dashboard() {
  const defaultRange = useMemo(() => getQuarterRange(), []);
  const rangePresets = useMemo(() => getRangePresets(), []);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [invoiceStart, setInvoiceStart] = useState(defaultRange.start);
  const [invoiceEnd, setInvoiceEnd] = useState(defaultRange.end);
  const [taskStart, setTaskStart] = useState(defaultRange.start);
  const [taskEnd, setTaskEnd] = useState(defaultRange.end);
  const [openStart, setOpenStart] = useState(defaultRange.start);
  const [openEnd, setOpenEnd] = useState(defaultRange.end);

  useEffect(() => {
    let isMounted = true;
    const loadTasks = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await apiRequest("/tasks/full");
        if (isMounted) {
          setTasks(Array.isArray(data?.tasks) ? data.tasks : []);
        }
      } catch (err) {
        if (isMounted) {
          setError(err?.message || "Failed to load tasks.");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    loadTasks();
    return () => {
      isMounted = false;
    };
  }, []);

  const invoicedTotal = useMemo(() => {
    return tasks
      .filter((task) => task?.invoiced)
      .filter((task) => isWithinRange(task?.date, invoiceStart, invoiceEnd))
      .reduce((sum, task) => sum + parseAmount(task?.sum), 0);
  }, [tasks, invoiceStart, invoiceEnd]);

  const tasksCount = useMemo(() => {
    return tasks.filter((task) => isWithinRange(task?.date, taskStart, taskEnd)).length;
  }, [tasks, taskStart, taskEnd]);

  const invoicedBreakdown = useMemo(() => {
    const totals = new Map();
    tasks
      .filter((task) => task?.invoiced)
      .filter((task) => isWithinRange(task?.date, invoiceStart, invoiceEnd))
      .forEach((task) => {
        const label = `${task?.customer_name || "Unknown"}`.trim() || "Unknown";
        const current = totals.get(label) || 0;
        totals.set(label, current + parseAmount(task?.sum));
      });
    return Array.from(totals.entries())
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);
  }, [tasks, invoiceStart, invoiceEnd]);

  const taskTypeBreakdown = useMemo(() => {
    const totals = new Map();
    tasks
      .filter((task) => isWithinRange(task?.date, taskStart, taskEnd))
      .forEach((task) => {
        const label = `${task?.tasktype || "Unknown"}`.trim() || "Unknown";
        const current = totals.get(label) || 0;
        totals.set(label, current + 1);
      });
    return Array.from(totals.entries())
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);
  }, [tasks, taskStart, taskEnd]);

  const openTasks = useMemo(() => {
    return tasks
      .filter((task) => !task?.invoiced)
      .filter((task) => isWithinRange(task?.date, openStart, openEnd));
  }, [tasks, openStart, openEnd]);

  const openTasksCount = useMemo(() => openTasks.length, [openTasks]);

  const openTasksTotal = useMemo(() => {
    return openTasks.reduce((sum, task) => sum + parseAmount(task?.sum), 0);
  }, [openTasks]);

  const customerTaskStatus = useMemo(() => {
    const totals = new Map();
    tasks.forEach((task) => {
      const customerName = `${task?.customer_name || "Unknown"}`.trim() || "Unknown";
      const current = totals.get(customerName) || { invoicedCount: 0, openCount: 0 };
      if (task?.invoiced) {
        current.invoicedCount += 1;
      } else {
        current.openCount += 1;
      }
      totals.set(customerName, current);
    });

    return Array.from(totals.entries())
      .map(([customerName, counts]) => ({ customerName, ...counts }))
      .sort((a, b) => a.customerName.localeCompare(b.customerName, "da"));
  }, [tasks]);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="font-serif text-4xl text-ink">ST Faktura</h1>
        <p className="max-w-2xl text-sm text-ink/70">
          Manage customers, tasks, and invoices from one place. Use the forms on the left to
          interact with the API running at {apiBase()}.
        </p>
        <p className="text-xs text-ink/50">Overview stats default to {defaultRange.label}.</p>
      </header>
      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      <div className="grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
        <StatWidget
          title="Invoiced amount"
          description="Sum of invoiced tasks within the selected date range."
        >
          <div className="flex flex-wrap gap-2">
            {rangePresets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className="rounded-full border border-sand/80 bg-white/80 px-3 py-1 text-xs font-semibold text-ink/70 transition hover:text-ink"
                onClick={() => {
                  setInvoiceStart(preset.start);
                  setInvoiceEnd(preset.end);
                }}
              >
                {preset.label}
                <span className="ml-1 text-ink/40">{preset.detail}</span>
              </button>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-[1fr_1fr]">
            <label className="space-y-1 text-sm text-ink/70">
              Start date
              <input
                className="input"
                type="date"
                value={invoiceStart}
                onChange={(event) => setInvoiceStart(event.target.value)}
              />
            </label>
            <label className="space-y-1 text-sm text-ink/70">
              End date
              <input
                className="input"
                type="date"
                value={invoiceEnd}
                onChange={(event) => setInvoiceEnd(event.target.value)}
              />
            </label>
          </div>
          <div className="rounded-2xl border border-sand/80 bg-paper/70 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/50">Total invoiced</p>
            <p className="mt-2 font-serif text-3xl text-ink">
              {loading ? "Loading..." : formatCurrency(invoicedTotal)}
            </p>
          </div>
          <div className="rounded-2xl border border-sand/80 bg-white/70 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/50">By customer</p>
            {loading ? (
              <p className="mt-3 text-sm text-ink/60">Loading...</p>
            ) : invoicedBreakdown.length ? (
              <div className="mt-3 space-y-2">
                {invoicedBreakdown.map((item) => (
                  <div key={item.label} className="flex items-center justify-between text-sm text-ink/70">
                    <span>{item.label}</span>
                    <span className="font-semibold text-ink">{formatCurrency(item.value)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-ink/60">No invoiced tasks in range.</p>
            )}
          </div>
        </StatWidget>
        <StatWidget
          title="Tasks created"
          description="Count of tasks created within the selected date range."
        >
          <div className="flex flex-wrap gap-2">
            {rangePresets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className="rounded-full border border-sand/80 bg-white/80 px-3 py-1 text-xs font-semibold text-ink/70 transition hover:text-ink"
                onClick={() => {
                  setTaskStart(preset.start);
                  setTaskEnd(preset.end);
                }}
              >
                {preset.label}
                <span className="ml-1 text-ink/40">{preset.detail}</span>
              </button>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-[1fr_1fr]">
            <label className="space-y-1 text-sm text-ink/70">
              Start date
              <input
                className="input"
                type="date"
                value={taskStart}
                onChange={(event) => setTaskStart(event.target.value)}
              />
            </label>
            <label className="space-y-1 text-sm text-ink/70">
              End date
              <input
                className="input"
                type="date"
                value={taskEnd}
                onChange={(event) => setTaskEnd(event.target.value)}
              />
            </label>
          </div>
          <div className="rounded-2xl border border-sand/80 bg-paper/70 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/50">Tasks in range</p>
            <p className="mt-2 font-serif text-3xl text-ink">
              {loading ? "Loading..." : tasksCount.toLocaleString("da-DK")}
            </p>
          </div>
          <div className="rounded-2xl border border-sand/80 bg-white/70 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/50">By task type</p>
            {loading ? (
              <p className="mt-3 text-sm text-ink/60">Loading...</p>
            ) : taskTypeBreakdown.length ? (
              <div className="mt-3 space-y-2">
                {taskTypeBreakdown.map((item) => (
                  <div key={item.label} className="flex items-center justify-between text-sm text-ink/70">
                    <span>{item.label}</span>
                    <span className="font-semibold text-ink">
                      {item.value.toLocaleString("da-DK")}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-ink/60">No tasks in range.</p>
            )}
          </div>
        </StatWidget>
        <StatWidget
          title="Open tickets"
          description="Tasks that are not invoiced within the selected date range."
        >
          <div className="flex flex-wrap gap-2">
            {rangePresets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className="rounded-full border border-sand/80 bg-white/80 px-3 py-1 text-xs font-semibold text-ink/70 transition hover:text-ink"
                onClick={() => {
                  setOpenStart(preset.start);
                  setOpenEnd(preset.end);
                }}
              >
                {preset.label}
                <span className="ml-1 text-ink/40">{preset.detail}</span>
              </button>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-[1fr_1fr]">
            <label className="space-y-1 text-sm text-ink/70">
              Start date
              <input
                className="input"
                type="date"
                value={openStart}
                onChange={(event) => setOpenStart(event.target.value)}
              />
            </label>
            <label className="space-y-1 text-sm text-ink/70">
              End date
              <input
                className="input"
                type="date"
                value={openEnd}
                onChange={(event) => setOpenEnd(event.target.value)}
              />
            </label>
          </div>
          <div className="rounded-2xl border border-sand/80 bg-paper/70 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/50">Open tickets</p>
            <p className="mt-2 font-serif text-3xl text-ink">
              {loading ? "Loading..." : openTasksCount.toLocaleString("da-DK")}
            </p>
          </div>
          <div className="rounded-2xl border border-sand/80 bg-white/70 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/50">Open value</p>
            <p className="mt-2 font-serif text-3xl text-ink">
              {loading ? "Loading..." : formatCurrency(openTasksTotal)}
            </p>
          </div>
        </StatWidget>
        <div className="lg:col-span-2 xl:col-span-3">
          <StatWidget
            title="Customer task status"
            description="Number of invoiced and open tasks per customer."
          >
            <div className="overflow-x-auto rounded-2xl border border-sand/80 bg-white/70">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-white/90 text-xs uppercase tracking-wide text-ink/60">
                  <tr>
                    <th className="px-4 py-3">Customer</th>
                    <th className="px-4 py-3 text-right">Invoiced tasks</th>
                    <th className="px-4 py-3 text-right">Open tasks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-sand/60">
                  {loading ? (
                    <tr>
                      <td className="px-4 py-6 text-center text-ink/60" colSpan={3}>
                        Loading customer status...
                      </td>
                    </tr>
                  ) : customerTaskStatus.length ? (
                    customerTaskStatus.map((item) => (
                      <tr key={item.customerName} className="hover:bg-white/70">
                        <td className="px-4 py-3 font-semibold text-ink">{item.customerName}</td>
                        <td className="px-4 py-3 text-right text-ink/80">
                          {item.invoicedCount.toLocaleString("da-DK")}
                        </td>
                        <td className="px-4 py-3 text-right text-ink/80">
                          {item.openCount.toLocaleString("da-DK")}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td className="px-4 py-6 text-center text-ink/60" colSpan={3}>
                        No task data available.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </StatWidget>
        </div>
      </div>
    </div>
  );
}
