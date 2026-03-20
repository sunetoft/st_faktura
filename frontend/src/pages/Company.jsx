import { useState } from "react";
import { apiRequest } from "../lib/api";

const initialForm = {
  company_name: "",
  company_address: "",
  company_cvr: "",
  company_zip: "",
  company_town: "",
  company_phone: "",
  company_email: "",
  bank_name: "",
  bank_account: "",
  iban: "",
  swift: "",
  additional_info: "",
};

export default function Company() {
  const [form, setForm] = useState(initialForm);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const update = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setStatus(null);
    try {
      const data = await apiRequest("/company-details", {
        method: "PUT",
        body: JSON.stringify(form),
      });
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
        <h1 className="font-serif text-3xl text-ink">Company info</h1>
        <p className="text-sm text-ink/70">Update the invoice header and banking details.</p>
      </header>
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        <input className="input" placeholder="Company name" value={form.company_name} onChange={update("company_name")} required />
        <input className="input" placeholder="Address" value={form.company_address} onChange={update("company_address")} required />
        <input className="input" placeholder="CVR" value={form.company_cvr} onChange={update("company_cvr")} required />
        <input className="input" placeholder="Zip" value={form.company_zip} onChange={update("company_zip")} required />
        <input className="input" placeholder="Town" value={form.company_town} onChange={update("company_town")} required />
        <input className="input" placeholder="Phone" value={form.company_phone} onChange={update("company_phone")} required />
        <input className="input" placeholder="Email" value={form.company_email} onChange={update("company_email")} required />
        <input className="input" placeholder="Bank name" value={form.bank_name} onChange={update("bank_name")} required />
        <input className="input" placeholder="Bank account" value={form.bank_account} onChange={update("bank_account")} required />
        <input className="input" placeholder="IBAN" value={form.iban} onChange={update("iban")} required />
        <input className="input" placeholder="SWIFT" value={form.swift} onChange={update("swift")} required />
        <textarea className="input md:col-span-2" rows={3} placeholder="Additional info" value={form.additional_info} onChange={update("additional_info")} />
        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Saving..." : "Save company details"}
        </button>
      </form>
      {status ? (
        <pre className={`rounded-xl p-4 text-xs ${status.ok ? "bg-emerald-50 text-emerald-900" : "bg-red-50 text-red-700"}`}>
{status.message}
        </pre>
      ) : null}
    </div>
  );
}
