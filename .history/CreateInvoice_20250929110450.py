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
import base64
from datetime import datetime
from gmail_oauth import get_gmail_access_token
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

def safe_int(value: str) -> int:
    """Safely parse an integer, defaulting to 0 on failure"""
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning(f"Invalid time_minutes value '{value}', defaulting to 0")
        return 0

# Spreadsheet configuration
SPREADSHEET_ID = "170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0"
CUSTOMER_SHEET_RANGE = "A:H"
TASKS_SHEET_RANGE = "Opgave!A:I"  # Use Danish sheet 'Opgave' with full columns

# Company details file
COMPANY_DETAILS_FILE = os.path.join(os.getcwd(), 'company_details.json')


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
                    # Expect columns: Date, Customer Name, Tasktype, Pricing Type, Task Description, Task Time (Minutes), ...
                    if row and len(row) >= 6 and row[1] == customer_name:
                        task = {
                            'date': row[0],
                            'customer_name': row[1],
                            'tasktype': row[2],
                            'description': row[4],        # Task Description
                            'time_minutes': row[5]       # Task Time (Minutes)
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
            auth_method = os.getenv('EMAIL_AUTH_METHOD', 'password').lower()
            # Validate credentials
            if not sender_email:
                logger.error("Sender email not configured in environment variables")
                return False
            if auth_method != 'oauth' and not sender_password:
                logger.error("Sender password not configured in environment variables")
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
            if auth_method == 'oauth':
                # Use Gmail XOAUTH2
                token = get_gmail_access_token(sender_email)
                if not token:
                    logger.error(f"Failed to obtain OAuth token for {sender_email}")
                    return False
                auth_string = f"user={sender_email}\x01auth=Bearer {token}\x01\x01"
                server.docmd('AUTH', 'XOAUTH2 ' + base64.b64encode(auth_string.encode()).decode())
            else:
                server.login(sender_email, sender_password)
            