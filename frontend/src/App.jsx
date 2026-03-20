import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Customers from "./pages/Customers";
import Tasks from "./pages/Tasks";
import Invoices from "./pages/Invoices";
import CreateInvoice from "./pages/CreateInvoice";
import InvoiceSearch from "./pages/InvoiceSearch";
import Company from "./pages/Company";
import Status from "./pages/Status";
import Manage from "./pages/Manage";

const navItems = [
  { to: "/", label: "Overview" },
  { to: "/customers", label: "Add customer" },
  { to: "/tasks", label: "Add task" },
  { to: "/invoices", label: "Invoices" },
  { to: "/create-invoice", label: "Create invoice" },
  { to: "/search", label: "Search invoices" },
  { to: "/company", label: "Company info" },
  { to: "/manage", label: "Manage" },
  { to: "/status", label: "API status" },
];

function Sidebar() {
  return (
    <aside className="flex flex-col gap-4 rounded-3xl border border-sand/70 bg-white/70 p-5 shadow-soft">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-ink/50">Workspace</p>
        <h2 className="font-serif text-2xl text-ink">ST Faktura</h2>
      </div>
      <nav className="flex flex-col gap-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
            end={item.to === "/"}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto rounded-2xl border border-sand/70 bg-paper/70 p-4 text-xs text-ink/70">
        Use the navigation to perform common actions.
      </div>
    </aside>
  );
}

function Layout({ children }) {
  return (
    <div className="min-h-screen p-6 md:p-10">
      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <Sidebar />
        <section className="rounded-3xl border border-sand/70 bg-white/60 p-6 shadow-soft">
          {children}
        </section>
      </div>
    </div>
  );
}

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/customers" element={<Customers />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/invoices" element={<Invoices />} />
          <Route path="/create-invoice" element={<CreateInvoice />} />
        <Route path="/search" element={<InvoiceSearch />} />
        <Route path="/company" element={<Company />} />
        <Route path="/manage" element={<Manage />} />
        <Route path="/status" element={<Status />} />
      </Routes>
    </Layout>
  );
}

export default App;
