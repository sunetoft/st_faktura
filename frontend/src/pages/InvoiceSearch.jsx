import { useState } from "react";
import { apiRequest } from "../lib/api";

const initialForm = {
  query: "",
  regex: false,
  case_sensitive: false,
};

export default function InvoiceSearch() {
  const [form, setForm] = useState(initialForm);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  const update = (field) => (event) => {
    const value = event.target.type === "checkbox" ? event.target.checked : event.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setStatus(null);
    setResults(null);
    try {
      const params = new URLSearchParams({
        query: form.query,
        regex: String(Boolean(form.regex)),
        case_sensitive: String(Boolean(form.case_sensitive)),
      });
      const data = await apiRequest(`/invoices/search?${params.toString()}`, {
        method: "GET",
      });
      setResults(data);
    } catch (error) {
      setStatus({ ok: false, message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const matches = results?.results || [];
  const formatDate = (value) => {
    if (!value) {
      return "";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleDateString();
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-serif text-3xl text-ink">Search invoices</h1>
        <p className="text-sm text-ink/70">Find PDF matches in stored invoices.</p>
      </header>
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        <input className="input" placeholder="Search query" value={form.query} onChange={update("query")} required />
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-ink/70">
            <input type="checkbox" checked={form.regex} onChange={update("regex")} /> Regex
          </label>
          <label className="flex items-center gap-2 text-sm text-ink/70">
            <input type="checkbox" checked={form.case_sensitive} onChange={update("case_sensitive")} /> Case sensitive
          </label>
        </div>
        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
      </form>
      {status ? (
        <div className={`rounded-xl p-4 text-xs ${status.ok ? "bg-emerald-50 text-emerald-900" : "bg-red-50 text-red-700"}`}>
          {status.message}
        </div>
      ) : null}
      {results ? (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-serif text-xl text-ink">Results</h2>
            <span className="text-xs uppercase tracking-[0.3em] text-ink/50">{results.source || "unknown"}</span>
          </div>
          {matches.length === 0 ? (
            <p className="text-sm text-ink/70">No matches found.</p>
          ) : (
            <div className="grid gap-4">
              {matches.map((item) => (
                <article key={item.file || item.blob} className="rounded-2xl border border-sand/70 bg-white/70 p-4 shadow-soft">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-ink">{item.name || item.file || item.blob}</p>
                      <p className="text-xs text-ink/60">{item.file || item.blob}</p>
                      {item.date ? <p className="text-xs text-ink/60">Invoice date: {formatDate(item.date)}</p> : null}
                    </div>
                    {item.url ? (
                      <a className="btn" href={item.url} target="_blank" rel="noreferrer">
                        Open PDF
                      </a>
                    ) : null}
                  </div>
                  <div className="mt-3 space-y-2">
                    {(item.matches || []).map((match, index) => (
                      <div key={`${item.file || item.blob}-${index}`} className="rounded-xl border border-sand/70 bg-paper/70 p-3 text-xs text-ink/80">
                        <p className="text-[10px] uppercase tracking-[0.3em] text-ink/50">Page {match.page}</p>
                        <div className="mt-2 space-y-2">
                          {(match.snippets || []).map((snippet, idx) => (
                            <p key={`${item.file || item.blob}-${index}-${idx}`}>{snippet}</p>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}
