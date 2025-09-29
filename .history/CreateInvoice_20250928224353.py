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
from datetime import datetime
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
TASKS_SHEET_RANGE = "Opgave!A:E"  # Tasks sheet (gid=1276274497)

# Company details file
COMPANY_DETAILS_FILE = os.path.join(os.getcwd(), 'st-faktura.json')


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
                            'email': row[7] if len(row) > 7 else ''
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
                    if row and len(row) >= 5:  # All required fields
                        if row[1] == customer_name:  # Customer name match
                            task = {
                                'date': row[0] if len(row) > 0 else '',
                                'customer_name': row[1] if len(row) > 1 else '',
                                'tasktype': row[2] if len(row) > 2 else '',
                                'description': row[3] if len(row) > 3 else '',
                                'time_minutes': row[4] if len(row) > 4 else '0'
                            }
                            customer_tasks.append(task)
            
            logger.info(f"Found {len(customer_tasks)} tasks for customer: {customer_name}")
            return customer_tasks
            
        except Exception as e:
            logger.error(f"Failed to retrieve tasks for customer {customer_name}: {e}")
            return []
    
    def load_company_details(self) -> Optional[Dict[str, str]]:
        """
        Load company details from file
        
        Returns:
            Dictionary containing company details or None if not found
        """
        try:
            if os.path.exists(COMPANY_DETAILS_FILE):
                with open(COMPANY_DETAILS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.error(f"Company details file not found: {COMPANY_DETAILS_FILE}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load company details: {e}")
            return None
    
    def generate_invoice(
        self,
        customer: Dict[str, str],
        selected_tasks: List[Dict[str, str]],
        hourly_rate: float = 500.0
    ) -> Optional[str]:
        """
        Generate an invoice PDF
        
        Args:
            customer: Customer information
            selected_tasks: List of selected tasks
            hourly_rate: Hourly rate for calculations
            
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
                hourly_rate=hourly_rate
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
        invoice_number: int
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
            sender_password = os.getenv('SENDER_PASSWORD', '')
            
            if not sender_email or not sender_password:
                logger.error("Email credentials not configured in environment variables")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = customer_email
            msg['Subject'] = f"Faktura #{invoice_number} - ST_Faktura"
            
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
            server.starttls()
            server.login(sender_email, sender_password)
            text = msg.as_string()
            server.sendmail(sender_email, customer_email, text)
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
    
    for i, task in enumerate(tasks, 1):
        minutes = int(task['time_minutes'])
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
            selection = input("Selection (or 'q' to quit): ").strip()
            
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


def get_hourly_rate() -> Optional[float]:
    """
    Get hourly rate from user input
    
    Returns:
        Hourly rate in DKK or None if cancelled
    """
    print("\n" + "="*60)
    print("HOURLY RATE")
    print("="*60)
    
    default_rate = float(os.getenv('HOURLY_RATE', '500.0'))
    
    while True:
        try:
            rate_input = input(f"Enter hourly rate in DKK (default: {default_rate:.0f}) or 'q' to quit: ").strip()
            
            if rate_input.lower() == 'q':
                return None
            
            # If empty, use default rate
            if not rate_input:
                return default_rate
            
            hourly_rate = float(rate_input)
            
            if hourly_rate > 0:
                return hourly_rate
            else:
                print("❌ Hourly rate must be greater than 0.")
                
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")


def calculate_invoice_summary(tasks: List[Dict[str, str]], hourly_rate: float = 500.0) -> None:
    """
    Display invoice summary with VAT calculation
    
    Args:
        tasks: List of selected tasks
        hourly_rate: Hourly rate for calculations
    """
    total_minutes = sum(int(task['time_minutes']) for task in tasks)
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


def main() -> None:
    """
    Main function for invoice creation
    """
    logger.info("Starting ST_Faktura Invoice Creation")
    
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
        
        print("\n" + "="*60)
        print("ST_FAKTURA - INVOICE CREATION")
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
        
        # Step 3: Set hourly rate
        print("\nStep 3: Set Hourly Rate")
        hourly_rate = get_hourly_rate()
        
        if not hourly_rate:
            print("\n⏭️ Invoice creation cancelled.")
            return
        
        # Step 4: Review and confirm
        calculate_invoice_summary(selected_tasks, hourly_rate)
        
        confirm = input("\nDo you want to generate this invoice? (y/N): ").strip().lower()
        
        if confirm != 'y':
            print("\n⏭️ Invoice creation cancelled.")
            return
        
        # Step 5: Generate invoice
        print("\nStep 5: Generating Invoice...")
        pdf_path = invoice_manager.generate_invoice(selected_customer, selected_tasks, hourly_rate)
        
        if not pdf_path:
            print("❌ Failed to generate invoice PDF")
            sys.exit(1)
        
        print(f"✅ Invoice PDF generated: {pdf_path}")
        
        # Step 6: Send email (optional)
        if selected_customer['email']:
            send_email = input(f"\nSend invoice to {selected_customer['email']}? (y/N): ").strip().lower()
            
            if send_email == 'y':
                # Extract invoice number from filename or use the one we just generated
                import re
                match = re.search(r'faktura_(\d+)_', pdf_path)
                current_invoice_number = int(match.group(1)) if match else 785
                
                if invoice_manager.send_invoice_email(
                    selected_customer['email'], 
                    pdf_path, 
                    selected_customer['name'], 
                    current_invoice_number
                ):
                    print(f"✅ Invoice sent to {selected_customer['email']}")
                else:
                    print("❌ Failed to send invoice email")
        
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