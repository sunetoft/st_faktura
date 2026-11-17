"""Regenerate one invoice PDF from the live Opgave sheet (no numbering side-effects).

Usage: python3 regen_invoice_pdf.py 836 [--date 2026-11-17]
"""
import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, "/opt/st_faktura")
os.chdir("/opt/st_faktura")

from dotenv import load_dotenv
load_dotenv("/opt/st_faktura/.env")

from CreateInvoice import InvoiceManager
from google_sheets_client import GoogleSheetsClient, SheetsConfig
import api  # reuse the exact task-key / invoiced-state helpers


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("invoice_number", type=int)
    ap.add_argument("--date", default=None, help="printed fakturadato YYYY-MM-DD")
    args = ap.parse_args()

    client = GoogleSheetsClient(config=SheetsConfig())
    all_tasks = api._load_tasks_sheet(client)
    invoiced = api._load_invoiced_tasks_safe()

    wanted = []
    for task in all_tasks:
        meta = invoiced.get(api._task_unique_key(task))
        if meta and int(meta.get("invoice_number", -1)) == args.invoice_number:
            wanted.append(task)
    if not wanted:
        print(f"No tasks recorded for invoice {args.invoice_number}")
        return 1

    customer_name = wanted[0]["customer_name"].strip()
    customers = InvoiceManager(client).get_customers()
    customer = next((c for c in customers if str(c.get("name", "")).strip() == customer_name), None)
    if not customer:
        print(f"Customer not found: {customer_name}")
        return 1

    invoice_date = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now()
    manager = InvoiceManager(client)
    company = manager.load_company_details()
    if not company:
        print("Company details unavailable")
        return 1
    pdf_path = manager.pdf_generator.generate_invoice_pdf(
        invoice_number=args.invoice_number,
        company_details=company,
        customer_details=customer,
        tasks=wanted,
        hourly_rate=float(customer.get("hourly_rate") or 500.0),
        invoice_date_override=invoice_date,
    )
    net = sum(float(str(t.get("sum", 0)).replace(",", ".")) for t in wanted)
    print(f"Tasks: {len(wanted)}  net={net:.2f}  moms={net*0.25:.2f}  total={net*1.25:.2f}")
    print(pdf_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
