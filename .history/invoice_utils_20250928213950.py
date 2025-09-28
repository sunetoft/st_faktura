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
    Matches the ST Digital invoice template design
    """
    
    def __init__(self):
        """Initialize PDF generator"""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Ensure invoices directory exists
        os.makedirs(INVOICES_DIR, exist_ok=True)
    
    def _setup_custom_styles(self) -> None:
        """Set up custom paragraph styles matching the template"""
        # Company name style (left side)
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        # Company details style
        self.styles.add(ParagraphStyle(
            name='CompanyDetails',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))
        
        # Logo/Company brand style (right side)
        self.styles.add(ParagraphStyle(
            name='CompanyBrand',
            parent=self.styles['Normal'],
            fontSize=24,
            textColor=colors.black,
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        ))
        
        # Invoice title style
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=colors.black,
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold',
            spaceAfter=10
        ))
        
        # Invoice info style
        self.styles.add(ParagraphStyle(
            name='InvoiceInfo',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))
        
        # Table header style
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica'
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
        Generate a PDF invoice matching the ST Digital template
        
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
            filename = f"faktura_{invoice_number}_{invoice_date.strftime('%Y%m%d')}.pdf"
            filepath = os.path.join(INVOICES_DIR, filename)
            
            logger.info(f"Generating invoice PDF: {filename}")
            
            # Create PDF with custom canvas for header/footer
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=2.5*cm,
                leftMargin=2.5*cm,
                topMargin=3*cm,
                bottomMargin=3*cm
            )
            
            # Build invoice content
            story = []
            
            # Header section - Company info and logo area
            story.append(self._create_header_section(company_details))
            story.append(Spacer(1, 20))
            
            # Invoice title and info section
            story.append(self._create_invoice_title_section(invoice_number, invoice_date))
            story.append(Spacer(1, 20))
            
            # Customer info section (left side only, as per template)
            story.append(self._create_customer_section(customer_details))
            story.append(Spacer(1, 30))
            
            # Items table
            story.append(self._create_items_table(tasks, hourly_rate))
            story.append(Spacer(1, 20))
            
            # Payment terms and banking info
            story.append(self._create_payment_section(company_details, invoice_date))
            
            # Build PDF with custom page template
            def add_page_elements(canvas, doc):
                self._draw_page_elements(canvas, doc, company_details)
            
            doc.build(story, onFirstPage=add_page_elements, onLaterPages=add_page_elements)
            
            logger.info(f"Invoice PDF generated successfully: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate invoice PDF: {e}")
            raise
    
    def _create_header_section(self, company_details: Dict[str, str]) -> Table:
        """Create the header section with company info and logo area"""
        # Left side - Company details
        company_info = f"""{company_details.get('company_name', '')}<br/>
{company_details.get('company_address', '')}<br/>
{company_details.get('company_zip', '')} {company_details.get('company_town', '')}<br/>
{company_details.get('company_cvr', 'Danmark')}"""
        
        # Right side - Logo/Brand area (matching "ST Digital" style)
        brand_name = company_details.get('company_name', 'ST Digital')
        logo_area = f'<font size="20"><b>{brand_name}</b></font>'
        
        # Create header table
        header_data = [[
            Paragraph(company_info, self.styles['CompanyDetails']),
            Paragraph(logo_area, self.styles['CompanyBrand'])
        ]]
        
        header_table = Table(header_data, colWidths=[10*cm, 8*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        
        return header_table
    
    def _create_invoice_title_section(self, invoice_number: int, invoice_date: datetime) -> Table:
        """Create the invoice title and info section"""
        # Right side - Invoice title and details
        invoice_info = f"""<b>FAKTURA</b><br/><br/>
Fakturanr. ............ {invoice_number}<br/>
Fakturadato ........... {invoice_date.strftime('%d.%m.%Y')}<br/>
Kundenr. ............. {invoice_number}14477<br/>
Side ................. 1 af 1"""
        
        # Create section table (empty left, content right)
        section_data = [['', Paragraph(invoice_info, self.styles['InvoiceInfo'])]]
        
        section_table = Table(section_data, colWidths=[10*cm, 8*cm])
        section_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (1, 0), (1, 0), 9),
        ]))
        
        return section_table
    
    def _create_customer_section(self, customer_details: Dict[str, str]) -> Paragraph:
        """Create customer information section (left side only)"""
        customer_info = f"""{customer_details.get('name', '')}<br/>
{customer_details.get('address', '')}<br/>
{customer_details.get('zip', '')} {customer_details.get('town', '')}<br/>
{customer_details.get('cvr', 'Danmark')}"""
        
        return Paragraph(customer_info, self.styles['CompanyDetails'])
    
    def _create_items_table(self, tasks: List[Dict[str, str]], hourly_rate: float) -> Table:
        """Create the items table matching the ST Digital template"""
        # Table headers matching the template
        headers = ['Nr.', 'Tekst', 'Antal', 'Enhed', 'Stk. pris', 'Pris']
        
        # Table data
        table_data = [headers]
        total_amount = 0.0
        
        # Group tasks or create a single line item (like in template)
        if tasks:
            # Calculate totals
            total_minutes = sum(int(task.get('time_minutes', 0)) for task in tasks)
            total_hours = total_minutes / 60.0
            
            # Create a single line item for all tasks (simplified like template)
            task_descriptions = []
            for task in tasks:
                task_type = task.get('tasktype', '')
                description = task.get('description', '')
                task_descriptions.append(f"{task_type}: {description}")
            
            # Create main service line
            item_description = "IT Services / Konsultation"
            if task_descriptions:
                item_description += f"<br/><font size='8'>{'; '.join(task_descriptions[:3])}</font>"
                if len(task_descriptions) > 3:
                    item_description += f"<br/><font size='8'>... og {len(task_descriptions) - 3} flere opgaver</font>"
            
            amount = total_hours * hourly_rate
            total_amount = amount
            
            table_data.append([
                '001',
                item_description,
                f"{total_hours:.2f}",
                'timer',
                f"{hourly_rate:.2f}",
                f"{amount:.2f}"
            ])
        
        # Add empty rows for spacing (like in template)
        for _ in range(3):
            table_data.append(['', '', '', '', '', ''])
        
        # Create table with proper column widths
        table = Table(table_data, colWidths=[1*cm, 8*cm, 1.5*cm, 1.5*cm, 2*cm, 2*cm])
        
        # Calculate VAT
        vat_rate = 0.25  # 25% Danish VAT
        subtotal = total_amount
        vat_amount = subtotal * vat_rate
        total_with_vat = subtotal + vat_amount
        
        # Add summary section
        summary_start_row = len(table_data)
        
        # Add separator line
        table_data.append(['', '', '', '', '', ''])
        
        # Add totals
        table_data.append(['', '', '', '', 'Subtotal :', f"{subtotal:.2f}"])
        table_data.append(['', '', '', '', '25,00% moms :', f"{vat_amount:.2f}"])  
        table_data.append(['', '', '', '', 'Total DKK :', f"{total_with_vat:.2f}"])
        
        # Recreate table with updated data
        table = Table(table_data, colWidths=[1*cm, 8*cm, 1.5*cm, 1.5*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            # Header row styling
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -4), 9),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Antal column
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),  # Stk. pris column  
            ('ALIGN', (5, 1), (5, -1), 'RIGHT'),  # Pris column
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
            
            # Summary section
            ('LINEABOVE', (4, -4), (-1, -4), 0.5, colors.black),
            ('FONTNAME', (4, -3), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (4, -3), (-1, -1), 9),
            ('FONTNAME', (4, -1), (-1, -1), 'Helvetica-Bold'),  # Total row bold
            ('ALIGN', (4, -3), (4, -1), 'RIGHT'),
            ('ALIGN', (5, -3), (5, -1), 'RIGHT'),
        ]))
        
        return table
    
    def _create_payment_section(self, company_details: Dict[str, str], invoice_date: datetime) -> Table:
        """Create payment terms and banking information section"""
        due_date = invoice_date + timedelta(days=8)
        
        # Payment terms (matching template format)
        payment_info = f"""<b>Betalingsbetingelser:</b> Netto 14 dage - forfalden {due_date.strftime('%d.%m.%Y')}<br/>
Beløbet indbetales til vor bank. <b>Bank Nordik</b> - Regnr.: <b>6506</b> / Kontonr.: <b>{company_details.get('bank_account', '3061152279')}</b><br/>
Fakturanr. <b>783</b> bedes anført ved bankoverførsel<br/><br/>
<i>Ved for sen betaling påregnes rente i henhold til gældende lovgivlning.</i>"""
        
        # Create payment section
        payment_data = [
            [Paragraph(payment_info, self.styles['CompanyDetails'])]
        ]
        
        payment_table = Table(payment_data, colWidths=[16*cm])
        payment_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
        ]))
        
        return payment_table
    
    def _draw_page_elements(self, canvas, doc, company_details: Dict[str, str]) -> None:
        """Draw footer and any additional page elements"""
        # Footer information (matching template)
        footer_text = f"""{company_details.get('company_name', 'ST Digital')} - {company_details.get('company_address', 'Baldersgade 69 2 th - 2200 Kbh. N.')} - CVR-nr.: {company_details.get('company_cvr', '18194104')}
Tlf.: {company_details.get('company_phone', '29439585')} - Mail: {company_details.get('company_email', 'sure@stdigital.dk')}
Bank: {company_details.get('bank_name', 'Bank Nordik')} - Kontonr.: {company_details.get('bank_account', '6506 / 3061152279')} - IBAN-nr.: DK9165063061152279 - SWIFT-kode: BANCDKKK"""
        
        # Draw footer
        canvas.setFont('Helvetica', 8)
        
        # Split footer into lines
        footer_lines = footer_text.split('\n')
        y_position = 2*cm
        
        for line in footer_lines:
            # Center the text
            text_width = canvas.stringWidth(line, 'Helvetica', 8)
            x_position = (A4[0] - text_width) / 2
            canvas.drawString(x_position, y_position, line)
            y_position -= 10
        
        # Draw a line above footer
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(0.5)
        canvas.line(2.5*cm, 2.5*cm, A4[0] - 2.5*cm, 2.5*cm)