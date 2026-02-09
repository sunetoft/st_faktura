import { apiBase } from "../lib/api";

function Tile({ title, body, href }) {
  return (
    <div className="rounded-2xl border border-sand/70 bg-white/70 p-5 shadow-soft">
      <h3 className="font-serif text-xl text-ink">{title}</h3>
      <p className="mt-2 text-sm text-ink/70">{body}</p>
      {href ? (
        <a className="mt-4 inline-flex items-center text-sm font-semibold text-accent" href={href}>
          Open
        </a>
      ) : null}
    </div>
  );
}

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="font-serif text-4xl text-ink">ST Faktura</h1>
        <p className="max-w-2xl text-sm text-ink/70">
          Manage customers, tasks, and invoices from one place. Use the forms on the left to
          interact with the API running at {apiBase()}.
        </p>
      </header>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Tile title="Add customer" body="Create a new customer entry with pricing and renewal data." />
        <Tile title="Add task" body="Log billable work tied to a customer and pricing mode." />
        <Tile title="Create invoice" body="Generate an invoice and send it by email." />
        <Tile title="Search invoices" body="Scan generated PDFs with a query." />
        <Tile title="Company details" body="Update invoice header and banking details." />
        <Tile title="API docs" body="Explore endpoints in Swagger UI." href="/docs" />
      </div>
    </div>
  );
}
