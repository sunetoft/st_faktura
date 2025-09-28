"""
ST_Faktura Invoice Generation Utilities

This module provides utilities for generating PDF invoices and managing invoice numbering.
Following copilot instructions for cross-platform compatibility, proper logging, and clean architecture.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

logger = logging.getLogger(__name__)

# Invoice configuration
INVOICE_NUMBERING_FILE = os.path.join(os.getcwd(), 'invoice_numbering.json')
INVOICES_DIR = os.path.join(os.getcwd(), 'invoices')


class InvoiceNumberManager:
    """
    Manages invoice numbering following clean architecture principles
    """
    
    def __init__(self, config_file: str = INVOICE_NUMBERING_FILE):
        """
        Initialize invoice number manager
        
        Args:
            config_file: Path to the invoice numbering configuration file
        """
        self.config_file = config_file
        
    def get_next_invoice_number(self) -> int:
        """
        Get the next invoice number
        
        Returns:
            Next invoice number
        """
        try:
            # Load current invoice number
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                current_number = config.get('current_invoice_number', 784)
            else:
                current_number = 784  # Start from 784 so next is 785
            
            # Increment and save
            next_number = current_number + 1
            self._save_invoice_number(next_number)
            
            logger.info(f"Generated invoice number: {next_number}")
            return next_number
            
        except Exception as e:
            logger.error(f"Failed to get next invoice number: {e}")
            # Fallback to starting number
            return 785
    
    def _save_invoice_number(self, invoice_number: int) -> None:
        """
        Save the current invoice number to file
        
        Args:
            invoice_number: Current invoice number to save
        """
        try:
            config = {'current_invoice_number': invoice_number}
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            logger.debug(f"Saved invoice number: {invoice_number}")
            
        except Exception as e:
            logger.error(f"Failed to save invoice number: {e}")


class InvoicePDFGenerator:
    """
    Generates PDF invoices following clean architecture principles
    """
    
    def __init__(self):
        """Initialize PDF generator"""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Ensure invoices directory exists
        os.makedirs(INVOICES_DIR, exist_ok=True)
    
    def _setup_custom_styles(self) -> None:
        """Set up custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='CompanyStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_LEFT,
            leftIndent=0
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomerStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_LEFT,
            leftIndent=0
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_RIGHT,
            rightIndent=0
        ))
    
    def generate_invoice_pdf(
        self,
        invoice_number: int,
        company_details: Dict[str, str],
        customer_details: Dict[str, str],
        tasks: List[Dict[str, str]],
        hourly_rate: float = 500.0
    ) -> str:
        """
        Generate a PDF invoice
        
        Args:
            invoice_number: Invoice number
            company_details: Company information
            customer_details: Customer information
            tasks: List of tasks to include in invoice
            hourly_rate: Hourly rate for calculations
            
        Returns:
            Path to generated PDF file
        """
        try:
            # Generate filename
            invoice_date = datetime.now()
            filename = f"invoice_{invoice_number}_{invoice_date.strftime('%Y%m%d')}.pdf"
            filepath = os.path.join(INVOICES_DIR, filename)
            
            logger.info(f"Generating invoice PDF: {filename}")
            
            # Create PDF document
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Build invoice content
            story = []
            
            # Title
            story.append(Paragraph("FAKTURA / INVOICE", self.styles['CustomTitle']))
            story.append(Spacer(1, 20))
            
            # Company and customer info table
            company_info = self._format_company_info(company_details)
            customer_info = self._format_customer_info(customer_details)
            
            # Invoice details
            invoice_date_str = invoice_date.strftime("%d-%m-%Y")
            due_date = invoice_date + timedelta(days=8)
            due_date_str = due_date.strftime("%d-%m-%Y")
            
            invoice_info = [
                f"<b>Faktura nr.:</b> {invoice_number}",
                f"<b>Faktura dato:</b> {invoice_date_str}",
                f"<b>Forfaldsdato:</b> {due_date_str}"
            ]
            
            # Create info table
            info_data = [
                [company_info, customer_info, "<br/>".join(invoice_info)]
            ]
            
            info_table = Table(info_data, colWidths=[6*cm, 6*cm, 6*cm])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('PADDING', (0, 0), (-1, -1), 10),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 30))
            
            # Tasks table
            tasks_table = self._create_tasks_table(tasks, hourly_rate)
            story.append(tasks_table)
            story.append(Spacer(1, 20))
            
            # Banking information
            banking_info = self._create_banking_info(company_details)
            story.append(banking_info)
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"Invoice PDF generated successfully: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate invoice PDF: {e}")
            raise
    
    def _format_company_info(self, company_details: Dict[str, str]) -> str:
        """Format company information for invoice"""
        return f"""<b>{company_details.get('company_name', '')}</b><br/>
{company_details.get('company_address', '')}<br/>
{company_details.get('company_zip', '')} {company_details.get('company_town', '')}<br/>
CVR: {company_details.get('company_cvr', '')}<br/>
Tlf: {company_details.get('company_phone', '')}<br/>
Email: {company_details.get('company_email', '')}"""
    
    def _format_customer_info(self, customer_details: Dict[str, str]) -> str:
        """Format customer information for invoice"""
        return f"""<b>Kunde:</b><br/>
<b>{customer_details.get('name', '')}</b><br/>
{customer_details.get('address', '')}<br/>
{customer_details.get('zip', '')} {customer_details.get('town', '')}<br/>
CVR: {customer_details.get('cvr', '')}<br/>
Tlf: {customer_details.get('phone', '')}<br/>
Email: {customer_details.get('email', '')}"""
    
    def _create_tasks_table(self, tasks: List[Dict[str, str]], hourly_rate: float) -> Table:
        """Create the tasks table for the invoice"""
        # Table headers
        headers = ['Dato', 'Opgave Type', 'Beskrivelse', 'Timer', 'Pris pr. time', 'Beløb']
        
        # Table data
        table_data = [headers]
        total_amount = 0.0
        
        for task in tasks:
            task_date = task.get('date', '')
            task_type = task.get('tasktype', '')
            description = task.get('description', '')
            minutes = int(task.get('time_minutes', 0))
            hours = minutes / 60.0
            
            amount = hours * hourly_rate
            total_amount += amount
            
            table_data.append([
                task_date,
                task_type,
                description[:50] + ('...' if len(description) > 50 else ''),
                f"{hours:.2f}",
                f"{hourly_rate:.2f} DKK",
                f"{amount:.2f} DKK"
            ])
        
        # Add total row
        table_data.append(['', '', '', '', '<b>I alt:</b>', f'<b>{total_amount:.2f} DKK</b>'])
        
        # Create table
        table = Table(table_data, colWidths=[2*cm, 2.5*cm, 6*cm, 1.5*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('ALIGN', (3, 1), (3, -2), 'RIGHT'),  # Hours column
            ('ALIGN', (4, 1), (4, -2), 'RIGHT'),  # Rate column
            ('ALIGN', (5, 1), (5, -2), 'RIGHT'),  # Amount column
            
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (4, -1), (5, -1), 'RIGHT'),
            ('TOPPADDING', (0, -1), (-1, -1), 12),
        ]))
        
        return table
    
    def _create_banking_info(self, company_details: Dict[str, str]) -> Table:
        """Create banking information table"""
        banking_data = [
            ['<b>Betalingsoplysninger:</b>', ''],
            ['Bank:', company_details.get('bank_name', '')],
            ['Kontonummer:', company_details.get('bank_account', '')],
            ['IBAN:', company_details.get('iban', '')],
            ['SWIFT:', company_details.get('swift', '')],
        ]
        
        banking_table = Table(banking_data, colWidths=[4*cm, 8*cm])
        banking_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))
        
        return banking_table