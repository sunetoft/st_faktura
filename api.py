from __future__ import annotations

import json
import os
import re
import tempfile
from urllib.parse import quote
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PyPDF2 import PdfReader

# Load environment variables from .env if present.
load_dotenv()

# Ensure temp-friendly defaults before importing invoice utilities.
os.environ.setdefault("INVOICES_DIR", "/tmp/invoices")
os.environ.setdefault("INVOICE_NUMBERING_FILE", "/tmp/invoice_numbering.json")

from google_sheets_client import GoogleSheetsClient
from CreateCustomer import CustomerManager
from CreateTask import TaskManager
from CreateInvoice import BOOKKEEPING_EMAIL, InvoiceManager, SPREADSHEET_ID, TASKS_SHEET_RANGE, upload_to_drive
from invoice_utils import InvoiceNumberManager, InvoicePDFGenerator
from Tool_MyCompanyDetails import CompanyDetailsManager
from storage_utils import (
    download_blob_to_path,
    get_env_bucket,
    get_env_prefix,
    list_blob_objects,
    read_json_from_gcs,
    write_json_to_gcs,
)

app = FastAPI(title="ST_Faktura API", version="1.0")

_frontend_dist = Path(__file__).resolve().parent / "frontend" / "dist"
if _frontend_dist.exists():
    assets_dir = _frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateCustomerRequest(BaseModel):
    customer_id: str
    company_name: str
    company_address: str
    company_cvr: str
    company_zip: str
    company_town: str
    company_phone: str
    company_email: str
    hourly_rate: str
    host_price: Optional[str] = ""
    renew_date: Optional[str] = ""


class UpdateCustomerRequest(BaseModel):
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_cvr: Optional[str] = None
    company_zip: Optional[str] = None
    company_town: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    hourly_rate: Optional[str] = None
    host_price: Optional[str] = None
    renew_date: Optional[str] = None


class CreateTaskRequest(BaseModel):
    customer_name: str
    tasktype: str
    pricing_type: str = Field(..., description="FixedPrice or HourlyPrice")
    description: str
    time_minutes: Optional[int] = None
    fixed_price: Optional[float] = None
    discount_percentage: Optional[float] = 0.0
    hourly_rate: Optional[float] = None


class UpdateTaskRequest(BaseModel):
    customer_name: Optional[str] = None
    tasktype: Optional[str] = None
    pricing_type: Optional[str] = None
    description: Optional[str] = None
    time_minutes: Optional[int] = None
    fixed_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    hourly_rate: Optional[float] = None
    invoice_status: Optional[str] = None


class CreateInvoiceRequest(BaseModel):
    customer_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    send_email: bool = True
    cc_emails: Optional[List[str]] = None
    cc_bookkeeping: bool = False
    allow_reinvoice: bool = False
    selected_task_ids: Optional[List[int]] = None


class InvoicePreviewRequest(BaseModel):
    customer_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    selected_task_ids: Optional[List[int]] = None
    allow_reinvoice: bool = False


class UpdateInvoiceNumberRequest(BaseModel):
    next_invoice_number: int


class UpdateCompanyDetailsRequest(BaseModel):
    company_name: str
    company_address: str
    company_cvr: str
    company_zip: str
    company_town: str
    company_phone: str
    company_email: str
    bank_name: str
    bank_account: str
    iban: str
    swift: str
    additional_info: Optional[str] = ""


def get_sheets_client() -> GoogleSheetsClient:
    return GoogleSheetsClient(auth_method="service_account")


def _payload_dict(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class GCSInvoiceNumberManager:
    def __init__(self, bucket: str, blob_name: str):
        self.bucket = bucket
        self.blob_name = blob_name

    def _load_current(self) -> int:
        data = read_json_from_gcs(self.bucket, self.blob_name, default={})
        try:
            return int(data.get("current_invoice_number", 784))
        except (TypeError, ValueError):
            return 784

    def get_next_invoice_number(self) -> int:
        current = self._load_current()
        next_number = current + 1
        write_json_to_gcs(
            self.bucket,
            self.blob_name,
            {"current_invoice_number": next_number}
        )
        return next_number

    def peek_next_invoice_number(self) -> int:
        current = self._load_current()
        return current + 1


def _format_key_number(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return ""
        raw = raw.replace(",", ".")
        try:
            num = float(raw)
        except ValueError:
            return value.strip()
    else:
        try:
            num = float(value)
        except (TypeError, ValueError):
            return str(value).strip()
    if num.is_integer():
        return str(int(num))
    return f"{num:.2f}".rstrip("0").rstrip(".")


def _normalize_key_parts(parts: List[str]) -> List[str]:
    if len(parts) < 9:
        return parts
    normalized = parts[:]
    normalized[0] = normalized[0].strip()
    normalized[1] = normalized[1].strip()
    normalized[2] = normalized[2].strip()
    normalized[3] = normalized[3].strip()
    normalized[4] = normalized[4].strip()[:120]
    normalized[5] = _format_key_number(normalized[5])
    normalized[6] = _format_key_number(normalized[6])
    normalized[7] = _format_key_number(normalized[7])
    normalized[8] = _format_key_number(normalized[8])
    return normalized


def _normalize_key_string(key: str) -> str:
    parts = key.split("|")
    normalized = _normalize_key_parts(parts)
    return "|".join(normalized)


def _task_unique_key(task: Dict[str, Any]) -> str:
    parts = [
        str(task.get("customer_name", "")),
        str(task.get("date", "")),
        str(task.get("tasktype", "")),
        str(task.get("pricing_type", "")),
        str(task.get("description", "")),
        str(task.get("time_minutes", "")),
        str(task.get("price", "")),
        str(task.get("discount_percentage", "")),
        str(task.get("sum", "")),
    ]
    normalized = _normalize_key_parts(parts)
    return "|".join(normalized)


def _load_invoiced_tasks(bucket: str, blob_name: str) -> Dict[str, Dict[str, str]]:
    data = read_json_from_gcs(bucket, blob_name, default={})
    if isinstance(data, dict):
        return data
    return {}


def _get_invoiced_tasks_blob() -> tuple[str, str]:
    bucket = get_env_bucket()
    prefix = get_env_prefix()
    return bucket, f"{prefix}/state/invoiced_tasks.json"


def _remove_invoiced_task_keys_gcs(bucket: str, blob_name: str, keys: Iterable[str]) -> None:
    invoiced = _load_invoiced_tasks(bucket, blob_name)
    updated = {key: value for key, value in invoiced.items() if key not in keys}
    _save_invoiced_tasks(bucket, blob_name, updated)


def _save_invoiced_tasks(bucket: str, blob_name: str, data: Dict[str, Dict[str, str]]) -> None:
    write_json_to_gcs(bucket, blob_name, data)


def _record_invoiced_tasks(
    bucket: str,
    blob_name: str,
    tasks: List[Dict[str, Any]],
    invoice_number: int
) -> None:
    invoiced = _load_invoiced_tasks(bucket, blob_name)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for task in tasks:
        key = _task_unique_key(task)
        invoiced[key] = {
            "invoice_number": invoice_number,
            "date": ts,
        }
    _save_invoiced_tasks(bucket, blob_name, invoiced)


def _load_invoiced_tasks_safe() -> Dict[str, Dict[str, str]]:
    bucket, invoiced_blob = _get_invoiced_tasks_blob()
    raw = _load_invoiced_tasks(bucket, invoiced_blob)
    normalized: Dict[str, Dict[str, str]] = {}
    for key, meta in raw.items():
        normalized_key = _normalize_key_string(key)
        if normalized_key not in normalized:
            normalized[normalized_key] = meta
    return normalized


def _annotate_tasks_with_invoiced(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        invoiced = _load_invoiced_tasks_safe()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"GCS not configured for invoiced tasks: {exc}") from exc
    for task in tasks:
        key = _task_unique_key(task)
        meta = invoiced.get(key)
        task["invoiced"] = bool(meta)
        if meta:
            task["invoice_number"] = meta.get("invoice_number")
            task["invoiced_at"] = meta.get("date")
    return tasks


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def _filter_tasks_by_date(tasks: List[Dict[str, Any]], start: Optional[str], end: Optional[str]) -> List[Dict[str, Any]]:
    if not start and not end:
        return tasks
    start_dt = _parse_date(start) if start else None
    end_dt = _parse_date(end) if end else None
    filtered: List[Dict[str, Any]] = []
    for task in tasks:
        try:
            task_dt = _parse_date(str(task.get("date", "")))
        except Exception:
            continue
        if start_dt and task_dt < start_dt:
            continue
        if end_dt and task_dt > end_dt:
            continue
        filtered.append(task)
    return filtered


def _load_tasks_sheet(client: GoogleSheetsClient) -> List[Dict[str, Any]]:
    tasks_data = client.read_sheet(SPREADSHEET_ID, TASKS_SHEET_RANGE)
    tasks: List[Dict[str, Any]] = []
    if not tasks_data or len(tasks_data) <= 1:
        return tasks
    for idx, row in enumerate(tasks_data[1:], start=2):
        if not row or len(row) < 9:
            continue
        tasks.append(
            {
                "row_index": idx,
                "date": row[0],
                "customer_name": row[1],
                "tasktype": row[2],
                "pricing_type": row[3],
                "description": row[4],
                "time_minutes": row[5],
                "price": row[6],
                "discount_percentage": row[7],
                "sum": row[8],
            }
        )
    return tasks


def _highlight_snippets(text: str, pattern: re.Pattern, max_snippets: int = 3, context: int = 40) -> List[str]:
    snippets: List[str] = []
    for i, match in enumerate(pattern.finditer(text)):
        if i >= max_snippets:
            break
        start, end = match.start(), match.end()
        left = max(0, start - context)
        right = min(len(text), end + context)
        segment = text[left:right].replace("\n", " ")
        snippets.append(segment)
    return snippets


def _search_pdf_text(pdf_path: str, pattern: re.Pattern) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    reader = PdfReader(pdf_path)
    for idx, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if not text:
            continue
        if pattern.search(text):
            results.append(
                {
                    "page": idx + 1,
                    "snippets": _highlight_snippets(text, pattern),
                }
            )
    return results


def _parse_float_value(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int_value(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _get_hourly_rate_for_customer(client: GoogleSheetsClient, customer_name: str) -> float:
    task_manager = TaskManager(client)
    customers = task_manager.get_customers()
    matched = next((c for c in customers if c.get("name") == customer_name), None)
    if not matched:
        return 500.0
    return _parse_float_value(matched.get("hourly_rate"), 500.0)


_CUSTOMER_FIELDS = [
    "customer_id",
    "company_name",
    "company_address",
    "company_cvr",
    "company_zip",
    "company_town",
    "company_phone",
    "company_email",
    "hourly_rate",
    "host_price",
    "renew_date",
]


def _is_customer_header(row: List[str]) -> bool:
    if not row:
        return False
    first = str(row[0]).strip().lower()
    return first in {"customer id", "customer_id"}


def _normalize_customer_row(row: List[str]) -> List[str]:
    padded = list(row or [])
    if len(padded) < len(_CUSTOMER_FIELDS):
        padded.extend([""] * (len(_CUSTOMER_FIELDS) - len(padded)))
    return padded[: len(_CUSTOMER_FIELDS)]


def _row_to_customer(row: List[str]) -> Dict[str, str]:
    normalized = _normalize_customer_row(row)
    return dict(zip(_CUSTOMER_FIELDS, [str(value) for value in normalized]))


def _find_customer_row(rows: List[List[str]], customer_id: str) -> Optional[int]:
    start_index = 1 if rows and _is_customer_header(rows[0]) else 0
    for idx, row in enumerate(rows[start_index:], start=start_index):
        if not row:
            continue
        if str(row[0]).strip() == customer_id:
            return idx
    return None


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    index_path = _frontend_dist / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ST Faktura</title>
    <style>
        :root {
            --ink: #141414;
            --paper: #f7f2e7;
            --accent: #d94f3d;
            --accent-2: #1b6e6b;
            --shadow: rgba(20, 20, 20, 0.12);
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "EB Garamond", "Garamond", "Times New Roman", serif;
            color: var(--ink);
            background:
                radial-gradient(1200px 500px at 20% -10%, #ffe8c2 0%, transparent 60%),
                radial-gradient(900px 600px at 90% 0%, #d6f1ef 0%, transparent 55%),
                var(--paper);
            min-height: 100vh;
        }
        header {
            padding: 48px 8vw 24px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        h1 {
            font-size: clamp(2.4rem, 6vw, 4.2rem);
            margin: 0;
            letter-spacing: 0.5px;
        }
        .tagline {
            font-size: clamp(1rem, 2.2vw, 1.3rem);
            max-width: 680px;
            line-height: 1.5;
        }
        main {
            padding: 0 8vw 64px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 18px;
        }
        .card {
            background: #fff8ed;
            border: 1px solid #f1e2c4;
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 10px 30px var(--shadow);
            min-height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .card h2 {
            margin: 0 0 8px;
            font-size: 1.2rem;
        }
        .card p {
            margin: 0 0 12px;
            font-size: 0.98rem;
            line-height: 1.45;
        }
        .btn {
            display: inline-block;
            padding: 8px 14px;
            border-radius: 999px;
            text-decoration: none;
            font-size: 0.95rem;
            background: var(--accent);
            color: #fff;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            box-shadow: 0 6px 14px rgba(217, 79, 61, 0.35);
            width: fit-content;
        }
        .btn.secondary {
            background: var(--accent-2);
            box-shadow: 0 6px 14px rgba(27, 110, 107, 0.35);
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        footer {
            padding: 24px 8vw 40px;
            font-size: 0.95rem;
            color: #4a4a4a;
        }
        .mono { font-family: "Courier New", Courier, monospace; }
    </style>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;600;700&display=swap" rel="stylesheet" />
</head>
<body>
    <header>
        <h1>ST Faktura</h1>
        <div class="tagline">
            Invoice ops, customer management, and task billing in one calm workspace.
            Use the API or keep an eye on the status here.
        </div>
    </header>
    <main>
        <section class="card">
            <h2>API Docs</h2>
            <p>Explore endpoints, payloads, and try requests directly in Swagger UI.</p>
            <a class="btn" href="/docs">Open Docs</a>
        </section>
        <section class="card">
            <h2>Health</h2>
            <p>Quick heartbeat check for load balancers and monitors.</p>
            <a class="btn secondary" href="/api/health">Check Health</a>
        </section>
        <section class="card">
            <h2>API Base</h2>
            <p>Use the endpoints programmatically. All data flows to Google Sheets.</p>
            <div class="mono">/customers · /tasks · /invoices</div>
        </section>
    </main>
    <footer>
        ST Faktura API · Minimal UI for quick access
    </footer>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/favicon.ico")
def favicon() -> Dict[str, str]:
    icon_path = _frontend_dist / "favicon.ico"
    if icon_path.exists():
        return FileResponse(icon_path)
    return {"status": "ok"}




@app.get("/api/health")
def api_health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/customers")
def list_customers() -> Dict[str, List[str]]:
    client = get_sheets_client()
    manager = CustomerManager(client)
    rows = manager.get_existing_customers()

    names: List[str] = []
    seen = set()

    if rows:
        header = rows[0]
        name_index = -1
        for idx, value in enumerate(header):
            if str(value).strip().lower() == "company name":
                name_index = idx
                break
        if name_index < 0 and len(header) > 1:
            name_index = 1
        if name_index >= 0:
            for row in rows[1:]:
                if len(row) <= name_index:
                    continue
                name = str(row[name_index]).strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                names.append(name)

    if not names:
        column_rows = client.read_sheet(manager.spreadsheet_id, "Kunder!B:B")
        for row in column_rows[1:]:
            if not row:
                continue
            name = str(row[0]).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            names.append(name)

    return {"customers": names}


@app.get("/customers/full")
def list_customers_full() -> Dict[str, Any]:
    client = get_sheets_client()
    manager = CustomerManager(client)
    rows = manager.get_existing_customers()
    if not rows:
        return {"customers": []}

    start_index = 1 if _is_customer_header(rows[0]) else 0
    customers: List[Dict[str, str]] = []
    for row in rows[start_index:]:
        if not row or not any(str(value).strip() for value in row):
            continue
        customers.append(_row_to_customer(row))
    return {"customers": customers}


@app.get("/tasktypes")
def list_tasktypes() -> Dict[str, List[str]]:
    client = get_sheets_client()
    task_manager = TaskManager(client)
    tasktypes = task_manager.get_task_types()
    return {"tasktypes": tasktypes}


@app.post("/customers")
def create_customer(payload: CreateCustomerRequest) -> Dict[str, Any]:
    client = get_sheets_client()
    manager = CustomerManager(client)
    manager.setup_spreadsheet_headers()
    ok = manager.add_customer(_payload_dict(payload))
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to create customer")
    return {"status": "created"}


@app.put("/customers/{customer_id}")
def update_customer(customer_id: str, payload: UpdateCustomerRequest) -> Dict[str, Any]:
    client = get_sheets_client()
    manager = CustomerManager(client)
    rows = manager.get_existing_customers()
    if not rows:
        raise HTTPException(status_code=404, detail="Customer not found")

    row_index = _find_customer_row(rows, customer_id)
    if row_index is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    existing = _row_to_customer(rows[row_index])
    updates = _payload_dict(payload)
    for field, value in updates.items():
        if value is not None:
            existing[field] = value

    updated_row = [existing[field] for field in _CUSTOMER_FIELDS]
    sheet_row = row_index + 1
    client.write_sheet(
        manager.spreadsheet_id,
        f"Kunder!A{sheet_row}:K{sheet_row}",
        [updated_row],
    )
    return {"status": "updated"}


@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: str) -> Dict[str, Any]:
    client = get_sheets_client()
    manager = CustomerManager(client)
    rows = manager.get_existing_customers()
    if not rows:
        raise HTTPException(status_code=404, detail="Customer not found")

    row_index = _find_customer_row(rows, customer_id)
    if row_index is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    sheet_row = row_index + 1
    empty_row = [""] * len(_CUSTOMER_FIELDS)
    client.write_sheet(
        manager.spreadsheet_id,
        f"Kunder!A{sheet_row}:K{sheet_row}",
        [empty_row],
    )
    return {"status": "deleted"}


@app.post("/tasks")
def create_task(payload: CreateTaskRequest) -> Dict[str, Any]:
    if payload.pricing_type not in ("FixedPrice", "HourlyPrice"):
        raise HTTPException(status_code=400, detail="pricing_type must be FixedPrice or HourlyPrice")

    client = get_sheets_client()
    task_manager = TaskManager(client)

    hourly_rate = payload.hourly_rate
    if hourly_rate is None:
        customers = task_manager.get_customers()
        matched = next((c for c in customers if c.get("name") == payload.customer_name), None)
        if not matched:
            raise HTTPException(status_code=404, detail="Customer not found")
        try:
            hourly_rate = float(matched.get("hourly_rate", 500))
        except (TypeError, ValueError):
            hourly_rate = 500.0

    if payload.pricing_type == "FixedPrice":
        if payload.fixed_price is None:
            raise HTTPException(status_code=400, detail="fixed_price required for FixedPrice")
        calculated_price = float(payload.fixed_price)
        time_minutes = payload.time_minutes or 0
    else:
        if payload.time_minutes is None or payload.time_minutes <= 0:
            raise HTTPException(status_code=400, detail="time_minutes required for HourlyPrice")
        time_minutes = payload.time_minutes
        calculated_price = (time_minutes / 60.0) * float(hourly_rate)

    discount = float(payload.discount_percentage or 0.0)
    final_sum = calculated_price * (1.0 - (discount / 100.0))

    task_data = {
        "customer_name": payload.customer_name,
        "tasktype": payload.tasktype,
        "pricing_type": payload.pricing_type,
        "description": payload.description,
        "time_minutes": int(time_minutes),
        "calculated_price": round(calculated_price, 2),
        "discount_percentage": round(discount, 2),
        "final_sum": round(final_sum, 2),
    }

    ok = task_manager.add_task(task_data)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to create task")
    return {"status": "created"}


@app.get("/tasks/full")
def list_tasks_full() -> Dict[str, Any]:
    client = get_sheets_client()
    tasks = _load_tasks_sheet(client)
    return {"tasks": _annotate_tasks_with_invoiced(tasks)}


@app.get("/tasks/search")
def search_tasks(
    customer_name: str = Query(..., min_length=1),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    client = get_sheets_client()
    tasks = _load_tasks_sheet(client)
    customer_tasks = [task for task in tasks if str(task.get("customer_name", "")).strip() == customer_name]
    filtered = _filter_tasks_by_date(customer_tasks, start_date, end_date)
    return {"tasks": _annotate_tasks_with_invoiced(filtered)}


@app.put("/tasks/{row_index}")
def update_task(row_index: int, payload: UpdateTaskRequest) -> Dict[str, Any]:
    client = get_sheets_client()
    tasks = _load_tasks_sheet(client)
    existing = next((task for task in tasks if task.get("row_index") == row_index), None)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    customer_name = payload.customer_name or str(existing.get("customer_name", "")).strip()
    tasktype = payload.tasktype or str(existing.get("tasktype", "")).strip()
    pricing_type = payload.pricing_type or str(existing.get("pricing_type", "")).strip()
    description = payload.description or str(existing.get("description", "")).strip()
    discount = payload.discount_percentage
    if discount is None:
        discount = _parse_float_value(existing.get("discount_percentage"), 0.0)

    if pricing_type not in ("FixedPrice", "HourlyPrice"):
        raise HTTPException(status_code=400, detail="pricing_type must be FixedPrice or HourlyPrice")

    if pricing_type == "FixedPrice":
        fixed_price = payload.fixed_price
        if fixed_price is None:
            fixed_price = _parse_float_value(existing.get("price"), 0.0)
        time_minutes = payload.time_minutes
        if time_minutes is None:
            time_minutes = _parse_int_value(existing.get("time_minutes"), 0)
        calculated_price = float(fixed_price)
    else:
        time_minutes = payload.time_minutes
        if time_minutes is None:
            time_minutes = _parse_int_value(existing.get("time_minutes"), 0)
        if time_minutes <= 0:
            raise HTTPException(status_code=400, detail="time_minutes required for HourlyPrice")
        hourly_rate = payload.hourly_rate
        if hourly_rate is None:
            hourly_rate = _get_hourly_rate_for_customer(client, customer_name)
        calculated_price = (time_minutes / 60.0) * float(hourly_rate)

    final_sum = calculated_price * (1.0 - (float(discount) / 100.0))

    date_value = str(existing.get("date") or datetime.now().strftime("%Y-%m-%d"))
    updated_row = [
        date_value,
        customer_name,
        tasktype,
        pricing_type,
        description,
        int(time_minutes),
        round(calculated_price, 2),
        round(float(discount), 2),
        round(final_sum, 2),
    ]

    updated_task = {
        "date": date_value,
        "customer_name": customer_name,
        "tasktype": tasktype,
        "pricing_type": pricing_type,
        "description": description,
        "time_minutes": int(time_minutes),
        "price": round(calculated_price, 2),
        "discount_percentage": round(float(discount), 2),
        "sum": round(final_sum, 2),
    }

    task_manager = TaskManager(client)
    sheet_name = TASKS_SHEET_RANGE.split("!")[0]
    client.write_sheet(
        task_manager.spreadsheet_id,
        f"{sheet_name}!A{row_index}:I{row_index}",
        [updated_row],
    )

    if payload.invoice_status:
        status_value = payload.invoice_status.lower()
        keys = {
            _task_unique_key(existing),
            _task_unique_key(updated_task),
        }
        try:
            bucket, invoiced_blob = _get_invoiced_tasks_blob()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"GCS not configured for invoiced tasks: {exc}") from exc
        if status_value == "open":
            _remove_invoiced_task_keys_gcs(bucket, invoiced_blob, keys)
        elif status_value == "invoiced":
            _remove_invoiced_task_keys_gcs(bucket, invoiced_blob, keys)
            _record_invoiced_tasks(bucket, invoiced_blob, [updated_task], 0)
    return {"status": "updated"}


@app.delete("/tasks/{row_index}")
def delete_task(row_index: int) -> Dict[str, Any]:
    client = get_sheets_client()
    tasks = _load_tasks_sheet(client)
    existing = next((task for task in tasks if task.get("row_index") == row_index), None)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    empty_row = [""] * 9
    task_manager = TaskManager(client)
    sheet_name = TASKS_SHEET_RANGE.split("!")[0]
    client.write_sheet(
        task_manager.spreadsheet_id,
        f"{sheet_name}!A{row_index}:I{row_index}",
        [empty_row],
    )
    return {"status": "deleted"}


@app.post("/invoices")
def create_invoice(payload: CreateInvoiceRequest) -> Dict[str, Any]:
    client = get_sheets_client()
    try:
        bucket, invoiced_blob = _get_invoiced_tasks_blob()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"GCS not configured for invoiced tasks: {exc}") from exc
    prefix = get_env_prefix()
    number_blob = f"{prefix}/state/invoice_numbering.json"
    invoice_number_manager = GCSInvoiceNumberManager(bucket, number_blob)

    invoice_manager = InvoiceManager(client, invoice_number_manager=invoice_number_manager)

    customers = invoice_manager.get_customers()
    customer = next((c for c in customers if c.get("name") == payload.customer_name), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    all_tasks = _load_tasks_sheet(client)
    tasks = [task for task in all_tasks if str(task.get("customer_name", "")).strip() == payload.customer_name]
    tasks = _filter_tasks_by_date(tasks, payload.start_date, payload.end_date)

    if payload.selected_task_ids:
        selected = set(payload.selected_task_ids)
        tasks = [task for task in tasks if int(task.get("row_index", -1)) in selected]
    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found for customer/date range")

    invoiced = _load_invoiced_tasks(bucket, invoiced_blob)
    already = []
    for task in tasks:
        key = _task_unique_key(task)
        if key in invoiced:
            already.append({"task": task, "meta": invoiced[key]})

    if already and not payload.allow_reinvoice:
        raise HTTPException(status_code=409, detail={"message": "Tasks already invoiced", "items": already})

    next_number = invoice_number_manager.peek_next_invoice_number()
    pdf_path = invoice_manager.generate_invoice(customer, tasks, hourly_rate=customer.get("hourly_rate", 500.0))
    if not pdf_path:
        raise HTTPException(status_code=500, detail="Failed to generate invoice PDF")

    emailed = False
    if payload.send_email:
        customer_email = str(customer.get("email", "")).strip()
        if not customer_email:
            raise HTTPException(status_code=400, detail="Customer email missing in Kunder sheet")
        cc_emails = list(payload.cc_emails or [])
        if payload.cc_bookkeeping:
            cc_emails.append(BOOKKEEPING_EMAIL)
        if cc_emails:
            cc_emails = sorted({email for email in cc_emails if email})
        else:
            cc_emails = None
        emailed = invoice_manager.send_invoice_email(
            customer_email=customer_email,
            pdf_path=pdf_path,
            customer_name=str(customer.get("name", "")),
            invoice_number=next_number,
            cc_emails=cc_emails,
        )
        if not emailed:
            detail = getattr(invoice_manager, "last_email_error", None) or "Failed to send invoice email"
            raise HTTPException(status_code=502, detail=detail)

    gcs_uri = None
    drive_uploaded = False
    drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip() or None
    if drive_folder_id:
        drive_uploaded = upload_to_drive(pdf_path, folder_id=drive_folder_id)

    _record_invoiced_tasks(bucket, invoiced_blob, tasks, next_number)

    return {
        "invoice_number": next_number,
        "pdf_uri": gcs_uri,
        "emailed": emailed,
        "drive_uploaded": drive_uploaded,
    }


@app.get("/invoice-number")
def get_invoice_number() -> Dict[str, Any]:
    try:
        bucket = get_env_bucket()
        prefix = get_env_prefix()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"GCS not configured for invoice numbering: {exc}") from exc
    number_blob = f"{prefix}/state/invoice_numbering.json"
    data = read_json_from_gcs(bucket, number_blob, default={})
    current = int(data.get("current_invoice_number", 784))
    return {
        "current_invoice_number": current,
        "next_invoice_number": current + 1,
        "source": "gcs",
    }


@app.put("/invoice-number")
def set_invoice_number(payload: UpdateInvoiceNumberRequest) -> Dict[str, Any]:
    if payload.next_invoice_number < 1:
        raise HTTPException(status_code=400, detail="next_invoice_number must be >= 1")
    current = payload.next_invoice_number - 1
    try:
        bucket = get_env_bucket()
        prefix = get_env_prefix()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"GCS not configured for invoice numbering: {exc}") from exc
    number_blob = f"{prefix}/state/invoice_numbering.json"
    write_json_to_gcs(bucket, number_blob, {"current_invoice_number": current})
    return {
        "current_invoice_number": current,
        "next_invoice_number": payload.next_invoice_number,
        "source": "gcs",
    }


@app.post("/invoices/preview")
def preview_invoice(payload: InvoicePreviewRequest) -> FileResponse:
    client = get_sheets_client()
    invoice_manager = InvoiceManager(client)

    customers = invoice_manager.get_customers()
    customer = next((c for c in customers if c.get("name") == payload.customer_name), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    all_tasks = _load_tasks_sheet(client)
    tasks = [task for task in all_tasks if str(task.get("customer_name", "")).strip() == payload.customer_name]
    tasks = _filter_tasks_by_date(tasks, payload.start_date, payload.end_date)

    if payload.selected_task_ids:
        selected = set(payload.selected_task_ids)
        tasks = [task for task in tasks if int(task.get("row_index", -1)) in selected]
    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found for customer/date range")

    try:
        bucket, invoiced_blob = _get_invoiced_tasks_blob()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"GCS not configured for invoiced tasks: {exc}") from exc
    number_blob = f"{get_env_prefix()}/state/invoice_numbering.json"
    invoice_number_manager = GCSInvoiceNumberManager(bucket, number_blob)
    next_number = invoice_number_manager.peek_next_invoice_number()

    invoiced = _load_invoiced_tasks(bucket, invoiced_blob)
    already = []
    for task in tasks:
        key = _task_unique_key(task)
        if key in invoiced:
            already.append({"task": task, "meta": invoiced[key]})
    if already and not payload.allow_reinvoice:
        raise HTTPException(status_code=409, detail={"message": "Tasks already invoiced", "items": already})

    company_details = invoice_manager.load_company_details()
    if not company_details:
        raise HTTPException(status_code=500, detail="Missing company details")

    pdf_generator = InvoicePDFGenerator()
    pdf_path = pdf_generator.generate_invoice_pdf(
        next_number,
        company_details,
        customer,
        tasks,
        hourly_rate=customer.get("hourly_rate", 500.0),
    )
    return FileResponse(pdf_path, media_type="application/pdf", filename=os.path.basename(pdf_path))


@app.get("/invoices/search")
def search_invoices(
    query: str = Query(..., min_length=1),
    regex: bool = False,
    case_sensitive: bool = False,
) -> Dict[str, Any]:
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(query if regex else re.escape(query), flags)

    local_dir = os.getenv("LOCAL_INVOICES_DIR", "Fakturaer").strip()
    if local_dir and os.path.isdir(local_dir):
        base_dir = os.path.abspath(local_dir)
        results: List[Dict[str, Any]] = []
        for root, _dirs, files in os.walk(local_dir):
            for filename in files:
                if not filename.lower().endswith(".pdf"):
                    continue
                local_path = os.path.join(root, filename)
                rel_path = os.path.relpath(local_path, base_dir)
                url_path = quote(rel_path.replace(os.sep, "/"))
                updated = datetime.fromtimestamp(os.path.getmtime(local_path))
                matches = _search_pdf_text(local_path, pattern)
                if matches:
                    results.append(
                        {
                            "file": local_path,
                            "name": filename,
                            "url": f"/invoices/local/{url_path}",
                            "date": updated.isoformat(),
                            "matches": matches,
                        }
                    )
        return {"results": results, "source": "local"}

    try:
        bucket = get_env_bucket()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    prefix = get_env_prefix()
    pdf_prefix = f"{prefix}/invoices/"

    results: List[Dict[str, Any]] = []
    for blob in list_blob_objects(bucket, pdf_prefix):
        if not blob.name.lower().endswith(".pdf"):
            continue
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, os.path.basename(blob.name))
            download_blob_to_path(bucket, blob.name, local_path)
            matches = _search_pdf_text(local_path, pattern)
            if matches:
                updated = blob.updated.isoformat() if blob.updated else None
                results.append(
                    {
                        "blob": blob.name,
                        "name": os.path.basename(blob.name),
                        "date": updated,
                        "matches": matches,
                    }
                )

    return {"results": results, "source": "gcs"}


@app.get("/invoices/local/{file_path:path}")
def get_local_invoice(file_path: str) -> FileResponse:
    local_dir = os.getenv("LOCAL_INVOICES_DIR", "Fakturaer").strip()
    if not local_dir:
        raise HTTPException(status_code=404, detail="Local invoices directory not configured")

    base_dir = os.path.abspath(local_dir)
    target_path = os.path.abspath(os.path.join(base_dir, file_path))
    if not target_path.startswith(base_dir + os.sep):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not target_path.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(target_path, media_type="application/pdf")


@app.put("/company-details")
def update_company_details(payload: UpdateCompanyDetailsRequest) -> Dict[str, Any]:
    manager = CompanyDetailsManager()
    ok = manager.save_to_google_sheets(_payload_dict(payload))
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to update company details")
    return {"status": "updated"}


@app.get("/{full_path:path}")
def spa_fallback(full_path: str) -> HTMLResponse:
    index_path = _frontend_dist / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Not found")

    candidate = (_frontend_dist / full_path).resolve()
    if candidate.is_file() and str(candidate).startswith(str(_frontend_dist)):
        return FileResponse(candidate)
    return FileResponse(index_path)
