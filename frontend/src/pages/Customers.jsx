import { useEffect, useState } from "react";
import { apiRequest } from "../lib/api";

const initialForm = {
  customer_id: "",
  company_name: "",
  company_address: "",
  company_cvr: "",
  company_zip: "",
  company_town: "",
  company_phone: "",
  company_email: "",
  hourly_rate: "",
  host_price: "",
  renew_date: "",
};

export default function Customers() {
  const [form, setForm] = useState(initialForm);
  const [customers, setCustomers] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tableStatus, setTableStatus] = useState(null);
  const [tableLoading, setTableLoading] = useState(false);
  const [editingId, setEditingId] = useState(null);

  const update = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const loadCustomers = async () => {
    setTableLoading(true);
    setTableStatus(null);
    try {
      const data = await apiRequest("/customers/full");
      setCustomers(data.customers || []);
    } catch (error) {
      setTableStatus({ ok: false, message: error.message });
    } finally {
      setTableLoading(false);
    }
  };

  useEffect(() => {
    loadCustomers();
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setStatus(null);
    try {
      const payload = { ...form };
      let data;
      if (editingId) {
        delete payload.customer_id;
        data = await apiRequest(`/customers/${encodeURIComponent(editingId)}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } else {
        data = await apiRequest("/customers", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      setStatus({ ok: true, message: JSON.stringify(data, null, 2) });
      setForm(initialForm);
      setEditingId(null);
      await loadCustomers();
    } catch (error) {
      setStatus({ ok: false, message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (customer) => {
    setEditingId(customer.customer_id);
    setForm({ ...initialForm, ...customer });
    setStatus(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm(initialForm);
  };

  const deleteCustomer = async (customerId) => {
    const confirmed = window.confirm("Delete this customer?");
    if (!confirmed) {
      return;
    }
    setTableStatus(null);
    try {
      const data = await apiRequest(`/customers/${encodeURIComponent(customerId)}`, {
        method: "DELETE",
      });
      setTableStatus({ ok: true, message: JSON.stringify(data, null, 2) });
      if (editingId === customerId) {
        cancelEdit();
      }
      await loadCustomers();
    } catch (error) {
      setTableStatus({ ok: false, message: error.message });
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-serif text-3xl text-ink">Customers</h1>
        <p className="text-sm text-ink/70">Create, update, or remove customer records stored in Google Sheets.</p>
      </header>
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        <input
          className="input"
          placeholder="Customer ID"
          value={form.customer_id}
          onChange={update("customer_id")}
          required
          disabled={!!editingId}
        />
        <input className="input" placeholder="Company name" value={form.company_name} onChange={update("company_name")} required />
        <input className="input" placeholder="Address" value={form.company_address} onChange={update("company_address")} required />
        <input className="input" placeholder="CVR" value={form.company_cvr} onChange={update("company_cvr")} required />
        <input className="input" placeholder="Zip" value={form.company_zip} onChange={update("company_zip")} required />
        <input className="input" placeholder="Town" value={form.company_town} onChange={update("company_town")} required />
        <input className="input" placeholder="Phone" value={form.company_phone} onChange={update("company_phone")} required />
        <input className="input" placeholder="Email" value={form.company_email} onChange={update("company_email")} required />
        <input className="input" placeholder="Hourly rate" value={form.hourly_rate} onChange={update("hourly_rate")} required />
        <input className="input" placeholder="Hosting price" value={form.host_price} onChange={update("host_price")} />
        <input className="input" placeholder="Renew date (d.m)" value={form.renew_date} onChange={update("renew_date")} />
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn" type="submit" disabled={loading}>
            {loading ? "Saving..." : editingId ? "Update customer" : "Save customer"}
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
          <h2 className="text-lg font-semibold text-ink">All customers</h2>
          <button className="btn-secondary" type="button" onClick={loadCustomers} disabled={tableLoading}>
            {tableLoading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {tableStatus ? (
          <pre className={`rounded-xl p-4 text-xs ${tableStatus.ok ? "bg-emerald-50 text-emerald-900" : "bg-red-50 text-red-700"}`}>
{tableStatus.message}
          </pre>
        ) : null}
        <div className="overflow-x-auto rounded-2xl border border-sand/70 bg-white/80 shadow-soft">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-white/90 text-xs uppercase tracking-wide text-ink/60">
              <tr>
                <th className="px-4 py-3">Customer ID</th>
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Phone</th>
                <th className="px-4 py-3">Hourly rate</th>
                <th className="px-4 py-3">Host price</th>
                <th className="px-4 py-3">Renew date</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sand/60">
              {customers.length === 0 ? (
                <tr>
                  <td className="px-4 py-6 text-center text-ink/60" colSpan={8}>
                    {tableLoading ? "Loading customers..." : "No customers found."}
                  </td>
                </tr>
              ) : (
                customers.map((customer) => (
                  <tr key={customer.customer_id} className="hover:bg-white/70">
                    <td className="px-4 py-3 font-semibold text-ink">{customer.customer_id}</td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-ink">{customer.company_name}</div>
                      <div className="text-xs text-ink/60">{customer.company_address}</div>
                    </td>
                    <td className="px-4 py-3 text-ink/80">{customer.company_email}</td>
                    <td className="px-4 py-3 text-ink/80">{customer.company_phone}</td>
                    <td className="px-4 py-3 text-ink/80">{customer.hourly_rate}</td>
                    <td className="px-4 py-3 text-ink/80">{customer.host_price || "-"}</td>
                    <td className="px-4 py-3 text-ink/80">{customer.renew_date || "-"}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button className="btn-secondary" type="button" onClick={() => startEdit(customer)}>
                          Edit
                        </button>
                        <button className="btn" type="button" onClick={() => deleteCustomer(customer.customer_id)}>
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
      </section>
    </div>
  );
}
