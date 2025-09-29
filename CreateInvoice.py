"""
ST_Faktura Invoice Creation Script

This script allows users to create invoices by selecting customers and tasks,
then generates PDF invoices and sends them to customers.

Customer data from: https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=0#gid=0
Tasks from: https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=1276274497#gid=1276274497

Following copilot instructions for cross-platform compatibility, proper logging, and clean architecture.
"""

import os
import json
import logging
import sys
import smtplib
import argparse
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

from google_sheets_client import GoogleSheetsClient, SheetsConfig, extract_spreadsheet_id
from invoice_utils import InvoiceNumberManager, InvoicePDFGenerator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('st_faktura_invoices.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Spreadsheet configuration
SPREADSHEET_ID = "170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0"
CUSTOMER_SHEET_RANGE = "Kunder!A:I"  # Customer sheet (including hourly rate)
TASKS_SHEET_RANGE = "Opgave!A:I"  # Extended tasks sheet with pricing, discount, sum
COMPANY_DETAILS_SHEET_RANGE = "Company Details!A2:L2"  # Single company details row (after headers)

# Company details file
COMPANY_DETAILS_FILE = os.path.join(os.getcwd(), 'st-faktura.json')
INVOICED_TASKS_FILE = os.path.join(os.getcwd(), 'invoiced_tasks.json')
BOOKKEEPING_EMAIL = os.getenv('BOOKKEEPING_EMAIL', 'indtaegt@ebogholderen.dk')


class InvoiceManager:
    """
    Manages invoice operations following clean architecture principles
    """
    
    def __init__(self, sheets_client: GoogleSheetsClient):
        """
        Initialize invoice manager
        
        Args:
            sheets_client: Configured Google Sheets client
        """
        self.sheets_client = sheets_client
        self.spreadsheet_id = SPREADSHEET_ID
        self.invoice_number_manager = InvoiceNumberManager()
        self.pdf_generator = InvoicePDFGenerator()
        
    def get_customers(self) -> List[Dict[str, str]]:
        """
        Retrieve all customers from the customer spreadsheet
        
        Returns:
            List of customer dictionaries
        """
        try:
            logger.info("Retrieving customers from spreadsheet")
            customers_data = self.sheets_client.read_sheet(self.spreadsheet_id, CUSTOMER_SHEET_RANGE)
            
            customers = []
            
            # Skip header row and process customer data
            if customers_data and len(customers_data) > 1:
                for row in customers_data[1:]:
                    if row and len(row) >= 2:  # At least ID and name
                        customer = {
                            'id': row[0] if len(row) > 0 else '',
                            'name': row[1] if len(row) > 1 else '',
                            'address': row[2] if len(row) > 2 else '',
                            'cvr': row[3] if len(row) > 3 else '',
                            'zip': row[4] if len(row) > 4 else '',
                            'town': row[5] if len(row) > 5 else '',
                            'phone': row[6] if len(row) > 6 else '',
                            'email': row[7] if len(row) > 7 else '',
                            'hourly_rate': float(row[8]) if len(row) > 8 and row[8] else 500.0
                        }
                        customers.append(customer)
            
            logger.info(f"Found {len(customers)} customers")
            return customers
            
        except Exception as e:
            logger.error(f"Failed to retrieve customers: {e}")
            return []
    
    def get_customer_tasks(self, customer_name: str) -> List[Dict[str, str]]:
        """
        Retrieve all tasks for a specific customer
        
        Args:
            customer_name: Name of the customer
            
        Returns:
            List of task dictionaries for the customer
        """
        try:
            logger.info(f"Retrieving tasks for customer: {customer_name}")
            tasks_data = self.sheets_client.read_sheet(self.spreadsheet_id, TASKS_SHEET_RANGE)
            
            customer_tasks = []
            
            # Skip header row and process task data
            if tasks_data and len(tasks_data) > 1:
                for row in tasks_data[1:]:
                    if row and len(row) >= 9 and row[1] == customer_name:  # Expect full row
                        task = {
                            'date': row[0],
                            'customer_name': row[1],
                            'tasktype': row[2],
                            'pricing_type': row[3],
                            'description': row[4],
                            'time_minutes': row[5],
                            'price': row[6],
                            'discount_percentage': row[7],
                            'sum': row[8]
                        }
                        customer_tasks.append(task)
            
            logger.info(f"Found {len(customer_tasks)} tasks for customer: {customer_name}")
            return customer_tasks
            
        except Exception as e:
            logger.error(f"Failed to retrieve tasks for customer {customer_name}: {e}")
            return []
    
    def load_company_details(self) -> Optional[Dict[str, str]]:
        """
        Load company details from JSON and override with Google Sheet values if present
        
        Returns:
            Dictionary containing company details or None if not found
        """
        try:
            base_details: Dict[str, str] = {}

            # 1. Load from local JSON (fallback/base)
            if os.path.exists(COMPANY_DETAILS_FILE):
                try:
                    with open(COMPANY_DETAILS_FILE, 'r', encoding='utf-8') as f:
                        base_details = json.load(f)
                except Exception as jf:
                    logger.warning(f"Failed reading local company details JSON: {jf}")
            else:
                logger.info("No local company details JSON file found; will rely on sheet if available")

            # Normalize keys expected downstream (ensure all keys exist)
            expected_keys = [
                'company_name','company_address','company_cvr','company_zip','company_town',
                'company_phone','company_email','bank_name','bank_account','iban','swift','additional_info',
                'payment_terms_days'
            ]
            for k in expected_keys:
                base_details.setdefault(k, '')

            # 2. Try to read from Google Sheet (sheet takes precedence)
            try:
                sheet_rows = self.sheets_client.read_sheet(self.spreadsheet_id, COMPANY_DETAILS_SHEET_RANGE)
                if sheet_rows and len(sheet_rows) >= 1:
                    row = sheet_rows[0]
                    # Map indices safely
                    mapping = {
                        0: 'company_name',
                        1: 'company_address',
                        2: 'company_cvr',
                        3: 'company_zip',
                        4: 'company_town',
                        5: 'company_phone',
                        6: 'company_email',
                        7: 'bank_name',
                        8: 'bank_account',
                        9: 'iban',
                        10: 'swift',
                        11: 'additional_info',
                        12: 'payment_terms_days'  # Optional extra column if added later
                    }
                    sheet_details: Dict[str, str] = {}
                    for idx, key in mapping.items():
                        if idx < len(row):
                            value = str(row[idx]).strip()
                            if value:  # Only override if non-empty
                                sheet_details[key] = value
                    # Merge (sheet overrides JSON)
                    if sheet_details:
                        base_details.update(sheet_details)
                        logger.info("Company details overridden with Google Sheet values (including bank info)")
                else:
                    logger.info("Company Details sheet row empty or missing; using JSON values only")
            except Exception as se:
                logger.warning(f"Failed to read company details from sheet: {se}")

            # If after all steps we still lack a company name treat as missing config
            if not base_details.get('company_name'):
                logger.error("Company name missing in both JSON and Sheet; cannot proceed")
                return None

            return base_details
                
        except Exception as e:
            logger.error(f"Failed to load company details: {e}")
            return None
    
    def generate_invoice(
        self,
        customer: Dict[str, str],
        selected_tasks: List[Dict[str, str]],
        hourly_rate: float = 500.0,
        credit_memo: bool = False
    ) -> Optional[str]:
        """
        Generate an invoice PDF
        
        Args:
            customer: Customer information
            selected_tasks: List of selected tasks
            hourly_rate: Hourly rate for calculations
            credit_memo: Flag indicating if this is a credit memo
            
        Returns:
            Path to generated PDF file or None if failed
        """
        try:
            # Load company details
            company_details = self.load_company_details()
            if not company_details:
                logger.error("Cannot generate invoice without company details")
                return None
            
            # Get next invoice number
            invoice_number = self.invoice_number_manager.get_next_invoice_number()
            
            # Generate PDF
            pdf_path = self.pdf_generator.generate_invoice_pdf(
                invoice_number=invoice_number,
                company_details=company_details,
                customer_details=customer,
                tasks=selected_tasks,
                hourly_rate=hourly_rate,
                credit_memo=credit_memo
            )
            
            logger.info(f"Invoice generated: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Failed to generate invoice: {e}")
            return None
    
    def send_invoice_email(
        self,
        customer_email: str,
        pdf_path: str,
        customer_name: str,
        invoice_number: int,
        cc_emails: Optional[List[str]] = None
    ) -> bool:
        """
        Send invoice via email
        
        Args:
            customer_email: Customer's email address
            pdf_path: Path to the PDF invoice
            customer_name: Customer's name
            invoice_number: Invoice number
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Email configuration from environment variables
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            sender_email = os.getenv('SENDER_EMAIL', '')
            auth_method = os.getenv('EMAIL_AUTH_METHOD', 'password').lower()
            sender_password = os.getenv('SENDER_PASSWORD', '') if auth_method == 'password' else ''
            
            if not sender_email:
                logger.error("SENDER_EMAIL not configured in environment variables")
                return False
            
            access_token = None
            if auth_method == 'oauth':
                try:
                    from gmail_oauth import get_gmail_access_token
                    access_token = get_gmail_access_token(sender_email)
                    if not access_token:
                        logger.error("Failed to obtain Gmail OAuth access token")
                        return False
                except ImportError:
                    logger.error("gmail_oauth module not found. Cannot use OAuth method.")
                    return False
            elif auth_method == 'password':
                if not sender_password:
                    logger.error("SENDER_PASSWORD missing for password auth. Set EMAIL_AUTH_METHOD=oauth to use OAuth instead.")
                    return False
            else:
                logger.error(f"Unknown EMAIL_AUTH_METHOD '{auth_method}'. Use 'password' or 'oauth'.")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = customer_email
            # Add CC header if provided
            cc_emails_clean: List[str] = []
            if cc_emails:
                for addr in cc_emails:
                    a = addr.strip()
                    if a and a not in cc_emails_clean and a.lower() != customer_email.lower():
                        cc_emails_clean.append(a)
            if cc_emails_clean:
                msg['Cc'] = ", ".join(cc_emails_clean)
            # Updated branding: use 'ST Digital'
            msg['Subject'] = f"Faktura #{invoice_number} - ST Digital"
            
            # Email body
            body = f"""
Kære {customer_name},

Vedhæftet finder du faktura #{invoice_number}.

Betalingsfristen er 8 dage fra fakturadato.

Med venlig hilsen,
ST_Faktura
"""
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Attach PDF
            with open(pdf_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= faktura_{invoice_number}.pdf'
            )
            msg.attach(part)
            
            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo()
            server.starttls()
            server.ehlo()
            if auth_method == 'oauth':
                # XOAUTH2 authentication
                import base64
                auth_string = f"user={sender_email}\x01auth=Bearer {access_token}\x01\x01".encode('utf-8')
                server.docmd('AUTH', 'XOAUTH2 ' + base64.b64encode(auth_string).decode('utf-8'))
            else:
                server.login(sender_email, sender_password)
            text = msg.as_string()
            # Aggregate all recipients (To + CC)
            all_recipients = [customer_email] + cc_emails_clean
            server.sendmail(sender_email, all_recipients, text)
            server.quit()
            
            logger.info(f"Invoice email sent to {customer_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send invoice email: {e}")
            return False


def display_customers(customers: List[Dict[str, str]]) -> None:
    """
    Display available customers for selection
    
    Args:
        customers: List of customer dictionaries
    """
    print("\n" + "="*60)
    print("AVAILABLE CUSTOMERS")
    print("="*60)
    
    for i, customer in enumerate(customers, 1):
        print(f"{i:2d}. {customer['name']} (ID: {customer['id']})")
        if customer['town']:
            print(f"     {customer['town']} - {customer['email']}")
    
    print("="*60)


def select_customer(customers: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """
    Allow user to select a customer
    
    Args:
        customers: List of available customers
        
    Returns:
        Selected customer dictionary or None if cancelled
    """
    if not customers:
        print("❌ No customers available. Please add customers first using CreateCustomer.py")
        return None
    
    display_customers(customers)
    
    while True:
        try:
            selection = input(f"\nSelect customer (1-{len(customers)}) or 'q' to quit: ").strip()
            
            if selection.lower() == 'q':
                return None
            
            customer_index = int(selection) - 1
            
            if 0 <= customer_index < len(customers):
                selected_customer = customers[customer_index]
                print(f"\n✅ Selected: {selected_customer['name']}")
                return selected_customer
            else:
                print(f"❌ Invalid selection. Please enter a number between 1 and {len(customers)}")
                
        except ValueError:
            print("❌ Invalid input. Please enter a number or 'q' to quit.")


def display_tasks(tasks: List[Dict[str, str]]) -> None:
    """
    Display customer tasks for selection
    
    Args:
        tasks: List of task dictionaries
    """
    print("\n" + "="*80)
    print("AVAILABLE TASKS")
    print("="*80)
    
    total_minutes = 0
    
    def safe_int(value) -> int:
        try:
            if value is None:
                return 0
            s = str(value).strip()
            if s == '':
                return 0
            return int(float(s))  # allow '180.0' as well
        except (ValueError, TypeError):
            return 0

    for i, task in enumerate(tasks, 1):
        minutes = safe_int(task.get('time_minutes'))
        hours = minutes / 60.0
        total_minutes += minutes
        
        print(f"{i:2d}. {task['date']} - {task['tasktype']}")
        print(f"    {task['description'][:60]}{'...' if len(task['description']) > 60 else ''}")
        print(f"    Time: {hours:.2f} hours ({minutes} minutes)")
        print()
    
    total_hours = total_minutes / 60.0
    print(f"Total time for all tasks: {total_hours:.2f} hours ({total_minutes} minutes)")
    print("="*80)


def select_tasks(tasks: List[Dict[str, str]]) -> Optional[List[Dict[str, str]]]:
    """
    Allow user to select tasks for invoice
    
    Args:
        tasks: List of available tasks
        
    Returns:
        List of selected tasks or None if cancelled
    """
    if not tasks:
        print("❌ No tasks available for this customer. Please add tasks first using CreateTask.py")
        return None
    
    display_tasks(tasks)
    
    print("\nSelect tasks to include in invoice:")
    print("Enter task numbers separated by commas (e.g., 1,3,5) or 'all' for all tasks")
    
    while True:
        try:
            selection = input("Selection (or 'q' to quit): ")

            if selection.lower() == 'q':
                return None
            
            if selection.lower() == 'all':
                return tasks
            
            # Parse comma-separated numbers
            task_indices = [int(x.strip()) - 1 for x in selection.split(',')]
            
            # Validate indices
            selected_tasks = []
            for index in task_indices:
                if 0 <= index < len(tasks):
                    selected_tasks.append(tasks[index])
                else:
                    print(f"❌ Invalid task number: {index + 1}")
                    break
            else:
                # All indices were valid
                if selected_tasks:
                    print(f"\n✅ Selected {len(selected_tasks)} tasks")
                    return selected_tasks
                else:
                    print("❌ No tasks selected")
            
        except ValueError:
            print("❌ Invalid input. Please enter numbers separated by commas.")



def calculate_invoice_summary(tasks: List[Dict[str, str]], hourly_rate: float = 500.0) -> None:
    """
    Display invoice summary with VAT calculation
    
    Args:
        tasks: List of selected tasks
        hourly_rate: Hourly rate for calculations
    """
    def safe_int(value) -> int:
        try:
            if value is None:
                return 0
            s = str(value).strip()
            if s == '':
                return 0
            return int(float(s))
        except (ValueError, TypeError):
            return 0

    total_minutes = sum(safe_int(task.get('time_minutes')) for task in tasks)
    total_hours = total_minutes / 60.0
    subtotal = total_hours * hourly_rate
    vat_amount = subtotal * 0.25  # 25% Danish VAT
    total_with_vat = subtotal + vat_amount
    
    print("\n" + "="*60)
    print("INVOICE SUMMARY")
    print("="*60)
    print(f"Number of tasks:   {len(tasks)}")
    print(f"Total time:        {total_hours:.2f} hours ({total_minutes} minutes)")
    print(f"Hourly rate:       {hourly_rate:.2f} DKK")
    print(f"Subtotal:          {subtotal:.2f} DKK")
    print(f"VAT (25%):         {vat_amount:.2f} DKK")
    print(f"Total incl. VAT:   {total_with_vat:.2f} DKK")
    print("="*60)


# ===== Invoiced task tracking helpers ===== #
def _load_invoiced_tasks() -> Dict[str, Dict[str, str]]:
    try:
        if os.path.exists(INVOICED_TASKS_FILE):
            with open(INVOICED_TASKS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        return {}
    except Exception as e:
        logger.warning(f"Failed to load invoiced tasks file: {e}")
        return {}

def _save_invoiced_tasks(data: Dict[str, Dict[str, str]]) -> None:
    try:
        with open(INVOICED_TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save invoiced tasks file: {e}")

def _task_unique_key(task: Dict[str, str]) -> str:
    parts = [
        task.get('customer_name','').strip(),
        task.get('date','').strip(),
        task.get('tasktype','').strip(),
        task.get('pricing_type','').strip(),
        task.get('description','').strip()[:120],
        str(task.get('time_minutes','')).strip(),
        str(task.get('price','')).strip(),
        str(task.get('discount_percentage','')).strip(),
        str(task.get('sum','')).strip(),
    ]
    return '|'.join(parts)

def warn_already_invoiced(tasks: List[Dict[str, str]]) -> bool:
    invoiced = _load_invoiced_tasks()
    already = []
    for t in tasks:
        key = _task_unique_key(t)
        if key in invoiced:
            meta = invoiced[key]
            already.append((t, meta))
    if not already:
        return True
    print("\n⚠️  The following selected tasks have already been invoiced:")
    for idx, (task, meta) in enumerate(already, 1):
        desc = task.get('description','')
        short_desc = (desc[:47] + '...') if len(desc) > 50 else desc
        print(f" {idx}. {task['date']} - {task['tasktype']} ({short_desc}) -> Faktura #{meta.get('invoice_number')} on {meta.get('date')}")
    while True:
        choice = input("Proceed anyway and include them again? (y/N): ").strip().lower()
        if choice == 'y':
            return True
        if choice in ('n',''):
            return False
        print("Please answer 'y' or 'n'.")

def record_invoiced_tasks(tasks: List[Dict[str, str]], invoice_number: int) -> None:
    invoiced = _load_invoiced_tasks()
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for t in tasks:
        key = _task_unique_key(t)
        invoiced[key] = {
            'invoice_number': invoice_number,
            'date': ts
        }
    _save_invoiced_tasks(invoiced)
    logger.info(f"Recorded {len(tasks)} tasks as invoiced (invoice #{invoice_number})")

def upload_to_drive(file_path: str, folder_name: str = 'stfaktura') -> None:
    """Upload a file to Google Drive or a Shared Drive folder.

    Shared Drive handling:
      - If GOOGLE_DRIVE_SHARED_DRIVE_ID is set, all operations use that Shared Drive (driveId, corpora='drive').
      - Folder search/creation and file upload always pass supportsAllDrives/includeItemsFromAllDrives when a shared drive is used.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.errors import HttpError
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        shared_drive_id = os.getenv('GOOGLE_DRIVE_SHARED_DRIVE_ID', '').strip() or None
        keyfile = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        creds = service_account.Credentials.from_service_account_file(keyfile, scopes=SCOPES)
        drive_service = build('drive', 'v3', credentials=creds, cache_discovery=False)

        def list_folders():
            if shared_drive_id:
                return drive_service.files().list(
                    q=("name='{0}' and mimeType='application/vnd.google-apps.folder' and trashed=false".format(folder_name)),
                    corpora='drive',
                    driveId=shared_drive_id,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    fields='files(id)'
                ).execute().get('files', [])
            else:
                return drive_service.files().list(
                    q=("name='{0}' and mimeType='application/vnd.google-apps.folder' and trashed=false".format(folder_name)),
                    spaces='drive',
                    fields='files(id)'
                ).execute().get('files', [])

        folders = list_folders()
        if folders:
            folder_id = folders[0]['id']
        else:
            meta = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
            if shared_drive_id:
                # For creation in a Shared Drive, parent must be the shared drive root (supply parents=[shared_drive_id])
                meta['parents'] = [shared_drive_id]
            folder = drive_service.files().create(
                body=meta,
                fields='id',
                supportsAllDrives=bool(shared_drive_id)
            ).execute()
            folder_id = folder.get('id')
            logger.info(f"Created folder '{folder_name}' (id={folder_id}) in {'Shared Drive' if shared_drive_id else 'My Drive'}")

        file_meta = {'name': os.path.basename(file_path), 'parents': [folder_id]}
        media = MediaFileUpload(file_path, mimetype='application/pdf')
        drive_service.files().create(
            body=file_meta,
            media_body=media,
            fields='id',
            supportsAllDrives=bool(shared_drive_id)
        ).execute()
        logger.info(f"Uploaded '{os.path.basename(file_path)}' to folder '{folder_name}' ({'Shared Drive' if shared_drive_id else 'My Drive'})")

    except HttpError as e:
        status = getattr(e, 'resp', {}).status if hasattr(e, 'resp') else 'unknown'
        reason = ''
        try:
            if hasattr(e, 'error_details') and e.error_details:
                reason = e.error_details[0].get('reason', '')
        except Exception:
            pass
        if status == 403 or reason in ('storageQuotaExceeded', 'teamDriveFileLimitExceeded'):
            msg = (
                "Could not upload invoice to Google Drive using a service account.\n"
                "- If you intended a Shared Drive: set GOOGLE_DRIVE_SHARED_DRIVE_ID and add the service account as a member.\n"
                "- Otherwise switch to OAuth user credentials (AUTH_METHOD=oauth)."
            )
            print(f"ERROR: {msg}")
            logger.error(msg.replace('Could not upload', 'ERROR: Could not upload'))
        elif status == 404 or reason == 'notFound':
            msg = (
                f"Shared Drive not found or inaccessible (ID={shared_drive_id}).\n"
                "- Verify the ID (it's from the URL of the shared drive).\n"
                "- Ensure the service account has at least Content Manager access."
            )
            print(f"ERROR: {msg}")
            logger.error(msg.replace('Shared Drive not found', 'ERROR: Shared Drive not found'))
        else:
            logger.error(f"Drive upload failed (HTTP {status}) reason={reason}: {e}")
    except Exception as e:
        logger.error(f"Failed to upload to Drive: {e}")


def Credit_memo() -> bool:
    """Prompt user whether to generate a Credit Memo instead of a standard Invoice."""
    choice = input("Generate a Credit Memo instead of an Invoice? (y/N): ").strip().lower()
    return choice == 'y'
    

def main() -> None:
    """
    Main function for invoice creation
    """
    logger.info("Starting ST_Faktura Invoice Creation")
    # Offer Credit Memo option
    credit_memo = Credit_memo()
    
    try:
        # Check if company details exist
        if not os.path.exists(COMPANY_DETAILS_FILE):
            print("❌ Company details not found!")
            print("Please run Tool_MyCompanyDetails.py first to set up your company information.")
            sys.exit(1)
        
        # Initialize Google Sheets client
        config = SheetsConfig()
        auth_method = os.getenv('AUTH_METHOD', 'service_account')
        client = GoogleSheetsClient(auth_method=auth_method, config=config)
        
        # Initialize invoice manager
        invoice_manager = InvoiceManager(client)

        # Parse CLI arguments (allow placed after credit memo prompt for minimal disruption)
        parser = argparse.ArgumentParser(description="Create and send an invoice")
        parser.add_argument('--no-preview', action='store_true', help='Skip detailed invoice preview (still asks final confirmation unless --yes)')
        parser.add_argument('--preview', action='store_true', help='Force show detailed invoice preview (default behavior)')
        parser.add_argument('-y','--yes', action='store_true', help='Assume yes to all confirmations (non-interactive)')
        args, unknown = parser.parse_known_args()

        print("\n" + "="*60)
        title = "KREDITNOTA" if credit_memo else "INVOICE CREATION"
        print(f"ST_FAKTURA - {title}")
        print("="*60)
        
        # Step 1: Select customer
        print("\nStep 1: Select Customer")
        customers = invoice_manager.get_customers()
        selected_customer = select_customer(customers)

        if not selected_customer:
            print("\n⏭️ Invoice creation cancelled.")
            return

        # Step 2: Select tasks
        print(f"\nStep 2: Select Tasks for {selected_customer['name']}")
        customer_tasks = invoice_manager.get_customer_tasks(selected_customer['name'])
        selected_tasks = select_tasks(customer_tasks)

        if not selected_tasks:
            print("\n⏭️ Invoice creation cancelled.")
            return
        
        # Step 3: Review and confirm
        hourly_rate = selected_customer['hourly_rate']
        print(f"\nUsing customer's hourly rate: {hourly_rate:.2f} DKK")
        calculate_invoice_summary(selected_tasks, hourly_rate)

        # Extended preview of invoice BEFORE number allocation & PDF generation
        def safe_int(value) -> int:
            try:
                if value is None:
                    return 0
                s = str(value).strip()
                if s == '':
                    return 0
                return int(float(s))
            except (ValueError, TypeError):
                return 0

        show_preview = (not args.no_preview) or args.preview
        if show_preview:
            try:
                # Peek invoice number (will not increment)
                peek_number = invoice_manager.invoice_number_manager.peek_next_invoice_number()
            except Exception:
                peek_number = 'N/A'
            print("\n" + "-"*60)
            print("INVOICE PREVIEW (Not yet generated)")
            print("-"*60)
            print(f"Prospective invoice number: {peek_number}")
            # Payment terms (attempt to derive due date similar to PDF logic)
            payment_terms_days = 8
            raw_ct = None
            try:
                # Lazy load company details (won't persist number) for due date; reuse loader
                cdetails = invoice_manager.load_company_details()
                if cdetails:
                    raw_ct = cdetails.get('payment_terms_days')
            except Exception:
                pass
            if raw_ct:
                try:
                    payment_terms_days = int(str(raw_ct).strip())
                except ValueError:
                    pt_env = os.getenv('PAYMENT_TERMS_DAYS')
                    if pt_env:
                        try:
                            payment_terms_days = int(pt_env.strip())
                        except ValueError:
                            pass
            else:
                pt_env = os.getenv('PAYMENT_TERMS_DAYS')
                if pt_env:
                    try:
                        payment_terms_days = int(pt_env.strip())
                    except ValueError:
                        pass
            issue_date = datetime.now()
            due_date = issue_date + timedelta(days=payment_terms_days)
            print(f"Issue date: {issue_date.strftime('%d.%m.%Y')}  |  Due date (net {payment_terms_days}): {due_date.strftime('%d.%m.%Y')}")
            print(f"Customer: {selected_customer.get('name','')}  CVR: {selected_customer.get('cvr','')}")
            print("Tasks:")
            total_minutes_preview = 0
            for idx, t in enumerate(selected_tasks, 1):
                m = safe_int(t.get('time_minutes'))
                total_minutes_preview += m
                desc = t.get('description','')
                short_desc = (desc[:70] + '...') if len(desc) > 73 else desc
                print(f" {idx:2d}. {t.get('date','')} | {t.get('tasktype','')} | {m} min | Sum: {t.get('sum','0')} | {short_desc}")
            print("-"*60)
            # Derived monetary summary from selected tasks' sum column
            subtotal_preview = 0.0
            for t in selected_tasks:
                try:
                    subtotal_preview += float(t.get('sum','0') or 0)
                except ValueError:
                    pass
            vat_preview = subtotal_preview * 0.25
            total_preview = subtotal_preview + vat_preview
            print(f"Subtotal (from task sums): {subtotal_preview:.2f} DKK")
            print(f"VAT 25%:                 {vat_preview:.2f} DKK")
            print(f"TOTAL incl. VAT:         {total_preview:.2f} DKK")
            print("-"*60)
        else:
            print("(Preview skipped) Use --preview to force showing it.")
        
        # Warn about tasks already invoiced; allow reselection instead of exit
        while True:
            if warn_already_invoiced(selected_tasks):
                break
            print("\nYou chose NOT to include already invoiced tasks.")
            print("You can now re-select tasks (exclude duplicates) or 'q' to abort.")
            selected_tasks = select_tasks(customer_tasks)
            if not selected_tasks:
                print("\n⏭️ Invoice creation cancelled.")
                return

        if args.yes:
            confirm = 'y'
            print("\n--yes supplied: proceeding without interactive confirmation.")
        else:
            confirm = input("\nDo you want to generate this invoice? (y/N): ").strip().lower()
        
        if confirm != 'y':
            # Offer chance to adjust tasks instead of hard cancel
            while True:
                adjust = input("Would you like to adjust the task selection instead? (y/N): ").strip().lower()
                if adjust == 'y':
                    selected_tasks = select_tasks(customer_tasks)
                    if not selected_tasks:
                        print("\n⏭️ Invoice creation cancelled.")
                        return
                    calculate_invoice_summary(selected_tasks, hourly_rate)
                    continue_confirm = input("Generate invoice now with updated tasks? (y/N): ").strip().lower()
                    if continue_confirm == 'y':
                        break
                    else:
                        continue  # allow further adjustments
                elif adjust in ('n',''):
                    print("\n⏭️ Invoice creation cancelled.")
                    return
                else:
                    print("Please answer 'y' or 'n'.")
        
        # Step 4: Generate invoice
        print("\nStep 4: Generating Invoice...")
        pdf_path = invoice_manager.generate_invoice(
            selected_customer,
            selected_tasks,
            hourly_rate * (-1 if credit_memo else 1),
            credit_memo=credit_memo
        )
        
        if not pdf_path:
            print("❌ Failed to generate invoice PDF")
            sys.exit(1)
        
        print(f"✅ Invoice PDF generated: {pdf_path}")
        # Save a copy to Google Drive
        upload_to_drive(pdf_path)
        # Extract invoice number to record tasks
        import re
        match = re.search(r'faktura_(\d+)_', pdf_path)
        generated_invoice_number = int(match.group(1)) if match else None
        if generated_invoice_number is not None:
            record_invoiced_tasks(selected_tasks, generated_invoice_number)
        
        # Step 5: Send email (optional)
        if selected_customer['email']:
            if args.yes:
                send_email = 'y'
                print(f"\n--yes supplied: auto-sending to {selected_customer['email']}")
            else:
                send_email = input(f"\nSend invoice to {selected_customer['email']}? (y/N): ").strip().lower()

            if send_email == 'y':
                # Extract invoice number from filename or use the one we just generated
                import re
                match = re.search(r'faktura_(\d+)_', pdf_path)
                current_invoice_number = int(match.group(1)) if match else 785
                
                # Optional CC prompt (single or comma separated)
                if args.yes:
                    cc_input = ''
                else:
                    cc_input = input("Enter additional CC email(s) (comma separated) or press Enter to skip: ").strip()
                cc_list: List[str] = []
                if cc_input:
                    # Split and basic validate
                    for raw in cc_input.split(','):
                        addr = raw.strip()
                        if addr and '@' in addr and addr not in cc_list:
                            cc_list.append(addr)
                if invoice_manager.send_invoice_email(
                    selected_customer['email'],
                    pdf_path,
                    selected_customer['name'],
                    current_invoice_number,
                    cc_emails=cc_list if cc_list else None
                ):
                    target_msg = selected_customer['email'] + (f" (CC: {', '.join(cc_list)})" if cc_list else "")
                    print(f"✅ Invoice sent to {target_msg}")
                else:
                    print("❌ Failed to send invoice email")

        # Step 6: Offer sending bookkeeping copy
        try:
            if BOOKKEEPING_EMAIL:
                # Skip bookkeeping prompt if already CC'ed
                skip_bookkeeping = False
                try:
                    last_cc = cc_list if 'cc_list' in locals() else []
                    for b in last_cc:
                        if b.lower() == BOOKKEEPING_EMAIL.lower():
                            skip_bookkeeping = True
                            break
                except Exception:
                    pass
                copy_choice = 'n'
                if not skip_bookkeeping:
                    if args.yes:
                        copy_choice = 'y'
                        print(f"\n--yes supplied: auto-sending bookkeeping copy to {BOOKKEEPING_EMAIL}")
                    else:
                        copy_choice = input(f"\nSend a copy to bookkeeping ({BOOKKEEPING_EMAIL})? (y/N): ").strip().lower()
                if copy_choice == 'y':
                    # reuse invoice number gathered above
                    if 'generated_invoice_number' not in locals() or generated_invoice_number is None:
                        import re
                        match_copy = re.search(r'faktura_(\d+)_', pdf_path)
                        generated_invoice_number = int(match_copy.group(1)) if match_copy else 0
                    if invoice_manager.send_invoice_email(
                        BOOKKEEPING_EMAIL,
                        pdf_path,
                        selected_customer['name'],
                        generated_invoice_number
                    ):
                        print(f"✅ Copy sent to {BOOKKEEPING_EMAIL}")
                    else:
                        print(f"❌ Failed to send copy to {BOOKKEEPING_EMAIL}")
        except Exception as e:
            logger.error(f"Error sending bookkeeping copy: {e}")
        
        print(f"\n🎉 Invoice creation completed successfully!")
        logger.info(f"Invoice creation completed for customer: {selected_customer['name']}")
    
    except KeyboardInterrupt:
        print("\n\n⏭️ Operation cancelled by user.")
        logger.info("Invoice creation interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Unexpected error in invoice creation: {e}")
        print(f"\n❌ An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()