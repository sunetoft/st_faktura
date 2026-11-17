# Agent Notes

## Running locally (production path)

launchd `dk.stdigital.invoice` → `uvicorn api:app --host 127.0.0.1 --port 18080`,
nginx `invoice.stdigital.dk` proxies to it, Cloudflare Access in front.

- After touching `api.py` / `invoice_utils.py` / `CreateInvoice.py`:
  `launchctl kickstart -k gui/$(id -u)/dk.stdigital.invoice`
- After touching `frontend/src`: `cd frontend && npm run build` (FastAPI serves `frontend/dist`).

Cloud Run deploy script (alternate path): `./deploy.sh`, optional env
`PROJECT_ID`, `REGION`, `SERVICE_NAME`.

## Money parsing — never `float()` a sheet value

`Opgave!A:I` is read with Google Sheets' default `FORMATTED_VALUE`, so da-DK locale
numbers arrive as strings like `"187,5"`. `float("187,5")` raises and silently zeroes
the subtotal/VAT/total (this produced invoice 836 with `Samlet pris 0,00`).
Always use `invoice_utils.parse_amount()` (also `api._parse_float_value`) and format
output with `invoice_utils.format_dkk()`. The total line prints currency:
`format_dkk(total, with_currency=True)` → `"DKK 234,38"` (since 17.11.2026).

## API surface (see `GET /capabilities`)

| Operation | Endpoint |
|---|---|
| Invoice list (totals from the issued PDF, cached by mtime) | `GET /invoices/list` |
| Invoice delete (releases tasks for re-invoicing) | `DELETE /invoices/{n}?delete_drive=&delete_pdf=` |
| Credit memo list / preview / create / delete | `GET /credit-memos/list`, `POST /credit-memos/preview`, `POST /credit-memos`, `DELETE /credit-memos/{n}?delete_drive=` |

The Invoices page renders its "API capability status" panel from `/capabilities`;
add new endpoints there instead of hard-coding labels in the UI. `GET /capabilities`
must stay declared before the SPA catch-all route `/{full_path:path}`.

## State

`data/st-faktura/state/invoiced_tasks.json` keys are
`customer|date|tasktype|pricing_type|description|time_minutes|price|discount|sum`
(net excl. VAT). The mapping has known drift, so invoice totals are read from the PDF
(`Samlet pris`) and only fall back to the state file (`total_source: "state"`).

`tools`: `python3 regen_invoice_pdf.py <n> [--date YYYY-MM-DD]` regenerates one PDF
from the live sheet without consuming an invoice number.
`python3 replace_drive_invoice_pdf.py <n>` overwrites the Drive copy **in place**
(same `fileId`, same name, revision kept) and verifies by re-downloading the md5 —
use this instead of re-uploading, which always creates a duplicate name in the folder.
