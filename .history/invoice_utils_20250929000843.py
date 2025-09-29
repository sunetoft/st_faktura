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
        # Modified to use new layout
        try:
            invoice_date = datetime.now()
            filename = f"faktura_{invoice_number}_{invoice_date.strftime('%Y%m%d')}.pdf"
            filepath = os.path.join(INVOICES_DIR, filename)
            logger.info(f"Generating invoice PDF (new layout): {filename}")
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=2.0*cm,
                leftMargin=2.0*cm,
                topMargin=2.0*cm,
                bottomMargin=2.0*cm
            )
            story = []
            story.append(self._create_new_header(invoice_number, invoice_date, company_details, customer_details))
            story.append(Spacer(1, 20))
            story.append(self._create_new_items_table(tasks, company_details))
            story.append(Spacer(1, 25))
            story.append(self._create_payment_section(company_details, invoice_date))
            def add_page_elements(canvas, doc):
                self._draw_page_elements(canvas, doc, company_details)
            doc.build(story, onFirstPage=add_page_elements, onLaterPages=add_page_elements)
            logger.info(f"Invoice PDF generated successfully: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to generate invoice PDF: {e}")
            raise

    def _create_new_header(self, invoice_number: int, invoice_date: datetime, company_details: Dict[str, str], customer_details: Dict[str, str]) -> Table:
        customer_block = f"""{customer_details.get('name','')}<br/>{customer_details.get('address','')}<br/>{customer_details.get('zip','')} {customer_details.get('town','')}"""
        # Right side: Logo + Fakturadato + Fakturanr.
        logo_text = company_details.get('company_name', 'ST Digital')
        header_info = f"""<font size='18'><b>{logo_text}</b></font><br/><br/>
Fakturadato: {invoice_date.strftime('%d.%m.%Y')}<br/>
Fakturanr.: {invoice_number}"""
        data = [
            [Paragraph(customer_block, self.styles['CompanyDetails']), Paragraph(header_info, self.styles['InvoiceInfo'])]
        ]
        table = Table(data, colWidths=[9*cm, 6*cm])
        table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT')
        ]))
        return table

    def _create_new_items_table(self, tasks: List[Dict[str, str]], company_details: Dict[str, str]) -> Table:
        headers = ['Tasktype', 'Task description', 'Min. forbrugt', 'Price', 'Discount %', 'Sum']
        data = [headers]
        subtotal = 0.0
        for t in tasks:
            tasktype = t.get('tasktype','')
            desc = t.get('description','')
            time_min = t.get('time_minutes','')
            price = t.get('price','0')
            discount = t.get('discount_percentage','0')
            line_sum = t.get('sum','0')
            try:
                subtotal += float(line_sum) if line_sum else 0.0
            except ValueError:
                pass
            data.append([
                tasktype,
                desc,
                time_min,
                price,
                discount,
                line_sum
            ])
        # Summary rows
        moms = subtotal * 0.25
        total = subtotal + moms
        data.append(['', '', '', '', 'Moms (25%)', f"{moms:.2f}"])
        data.append(['', '', '', '', 'Samlet pris', f"{total:.2f}"])
        table = Table(data, colWidths=[3*cm, 6*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.4*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('LINEBELOW', (0,0), (-1,0), 0.5, colors.black),
            ('ALIGN', (2,1), (2,-3), 'RIGHT'),
            ('ALIGN', (3,1), (5,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LINEABOVE', (4,-2), (5,-2), 0.5, colors.black),
            ('FONTNAME', (4,-1), (5,-1), 'Helvetica-Bold'),
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