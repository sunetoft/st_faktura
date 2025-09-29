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

# Unified content width (page width minus left/right margins: 2cm each)
CONTENT_SIDE_MARGIN = 2.0 * cm
CONTENT_WIDTH = A4[0] - (CONTENT_SIDE_MARGIN * 2)

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
        hourly_rate: float = 500.0,
        credit_memo: bool = False
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
        # If this is a credit memo, invert task sums and prices
        if credit_memo:
            formatted_tasks: List[Dict[str, str]] = []
            for t in tasks:
                try:
                    inv_sum = -float(t.get('sum', 0))
                except:
                    inv_sum = 0.0
                try:
                    inv_price = -float(t.get('price', 0))
                except:
                    inv_price = 0.0
                new_task = dict(t)
                new_task['sum'] = f"{inv_sum:.2f}"
                new_task['price'] = f"{inv_price:.2f}"
                formatted_tasks.append(new_task)
            tasks = formatted_tasks

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
            # Thin horizontal rule under header
            from reportlab.platypus import Table as RLTable
            rule_table = RLTable([[" "]], colWidths=[CONTENT_WIDTH], rowHeights=[2])
            rule_table.setStyle(TableStyle([
                ('LINEBELOW', (0,0), (-1,0), 0.5, colors.black),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(rule_table)
            story.append(Spacer(1, 16))  # Slightly larger gap after rule
            # Insert title above items table: 'Faktura' or 'Kreditnota'
            from reportlab.platypus import Paragraph
            title_text = "Kreditnota" if credit_memo else "Faktura"
            story.append(Paragraph(f"<para alignment='left'><b>{title_text}</b></para>", self.styles['InvoiceInfo']))
            story.append(Spacer(1, 18))  # More space between title and items table per request
            story.append(self._create_new_items_table(tasks, company_details))
            story.append(Spacer(1, 25))
            story.append(self._create_payment_section(company_details, invoice_date, invoice_number))
            def add_page_elements(canvas, doc):
                self._draw_page_elements(canvas, doc, company_details)
            doc.build(story, onFirstPage=add_page_elements, onLaterPages=add_page_elements)
            logger.info(f"Invoice PDF generated successfully: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to generate invoice PDF: {e}")
            raise

    def _create_new_header(self, invoice_number: int, invoice_date: datetime, company_details: Dict[str, str], customer_details: Dict[str, str]) -> Table:
        # Unified content width based on left/right page margins (2cm each) => usable width ~ (A4 width - 4cm)
        total_content_width = CONTENT_WIDTH
        # Allocate a fixed right column width for the meta/logo block; remaining width for customer block
        right_col_width = 6.5 * cm  # Fixed width ensures consistent alignment with items table
        left_col_width = total_content_width - right_col_width

        # Build customer block (filter out empty lines)
        customer_block_lines = [
            customer_details.get('name', ''),
            customer_details.get('address', ''),
            f"{customer_details.get('zip','')} {customer_details.get('town','')}".strip()
        ]
        customer_block = '<br/>'.join([l for l in customer_block_lines if l])

        # Attempt to load logo.gif; if not present fallback to text brand
        logo_path = os.path.join(os.getcwd(), 'logo.gif')
        brand_block_flowables = []
        if os.path.exists(logo_path):
            try:
                img = Image(logo_path)
                target_height = 40  # doubled (100% bigger) per request
                aspect = img.imageWidth / float(img.imageHeight) if img.imageHeight else 1.0
                img.drawHeight = target_height
                img.drawWidth = target_height * aspect
                brand_block_flowables.append(img)
            except Exception:
                logo_text = company_details.get('company_name', 'ST Digital')
                brand_block_flowables.append(Paragraph(f"<font size='20'><b>{logo_text}</b></font>", self.styles['CompanyDetails']))
        else:
            logo_text = company_details.get('company_name', 'ST Digital')
            brand_block_flowables.append(Paragraph(f"<font size='20'><b>{logo_text}</b></font>", self.styles['CompanyDetails']))

        # Add meta info (date + number)
        meta_html = (
            f"Fakturadato: {invoice_date.strftime('%d.%m.%Y')}<br/>"
            f"Fakturanr.: {invoice_number}"
        )
        brand_block_flowables.append(Paragraph(meta_html, self.styles['InvoiceInfo']))

        # Nested table on right for brand + meta, right aligned
        from reportlab.platypus import Table as RLTable
        right_table = RLTable([[f] for f in brand_block_flowables], colWidths=[right_col_width])
        right_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))

        row = [Paragraph(customer_block, self.styles['CompanyDetails']), right_table]
        table = Table([row], colWidths=[left_col_width, right_col_width])
        table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
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
        # Column width proportions originally based on 18cm total; rescale to CONTENT_WIDTH
        fractions = [0.1667, 0.3333, 0.1222, 0.1222, 0.1222, 0.1334]  # sum ~ 1.0
        col_widths = [CONTENT_WIDTH * f for f in fractions]
        table = Table(data, colWidths=col_widths)
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
    
    def _create_payment_section(self, company_details: Dict[str, str], invoice_date: datetime, invoice_number: int) -> Table:
        """Create payment terms and banking information section

        Priority for payment terms days:
        1. company_details['payment_terms_days'] if set and valid int
        2. ENV PAYMENT_TERMS_DAYS
        3. Fallback 8
        """
        # Determine payment terms days
        import os
        payment_terms_days = 8
        # From company details
        raw_ct = company_details.get('payment_terms_days') if company_details else None
        if raw_ct:
            try:
                payment_terms_days = int(str(raw_ct).strip())
            except ValueError:
                pass
        else:
            # From environment
            env_days = os.getenv('PAYMENT_TERMS_DAYS')
            if env_days:
                try:
                    payment_terms_days = int(env_days.strip())
                except ValueError:
                    pass

        due_date = invoice_date + timedelta(days=payment_terms_days)
        bank_name = company_details.get('bank_name', '') or 'Bank'
        bank_account = company_details.get('bank_account', '') or ''
        regnr = ''
        if bank_account and '/' in bank_account:
            parts = [p.strip() for p in bank_account.split('/')]
            if len(parts) == 2 and parts[0].replace(' ', '').isdigit():
                regnr = parts[0]
        payment_info = f"""<b>Betalingsbetingelser:</b> Netto {payment_terms_days} dage - forfalden {due_date.strftime('%d.%m.%Y')}<br/>
Beløbet indbetales til vor bank. <b>{bank_name}</b>{f' - Regnr.: <b>{regnr}</b>' if regnr else ''}{f' / Kontonr.: <b>{bank_account}</b>' if bank_account else ''}<br/>
Fakturanr. <b>{invoice_number}</b> bedes anført ved bankoverførsel<br/><br/>
<i>Ved for sen betaling påregnes rente i henhold til gældende lovgivning.</i>"""
        
        # Create payment section
        payment_data = [
            [Paragraph(payment_info, self.styles['CompanyDetails'])]
        ]
        
    # Use unified CONTENT_WIDTH for payment section to align with other elements
    payment_table = Table(payment_data, colWidths=[CONTENT_WIDTH])
        payment_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
        ]))
        
        return payment_table
    
    def _draw_page_elements(self, canvas, doc, company_details: Dict[str, str]) -> None:
        """Draw footer dynamically from company details file"""
        name = company_details.get('company_name', '')
        address = company_details.get('company_address', '')
        zip_code = company_details.get('company_zip', '')
        town = company_details.get('company_town', '')
        cvr = company_details.get('company_cvr', '')
        phone = company_details.get('company_phone', '')
        email = company_details.get('company_email', '')
        bank_name = company_details.get('bank_name', '')
        bank_account = company_details.get('bank_account', '')
        iban = company_details.get('iban', '')
        swift = company_details.get('swift', '')
        extra = company_details.get('additional_info', '')

        footer_lines = []
        line1_parts = [p for p in [name, address, f"{zip_code} {town}".strip(), f"CVR: {cvr}" if cvr else ''] if p]
        if line1_parts:
            footer_lines.append(" - ".join(line1_parts))
        line2_parts = [p for p in [f"Tlf.: {phone}" if phone else '', f"Mail: {email}" if email else ''] if p]
        if line2_parts:
            footer_lines.append(" - ".join(line2_parts))
        line3_parts = [p for p in [f"Bank: {bank_name}" if bank_name else '', f"Konto: {bank_account}" if bank_account else '', f"IBAN: {iban}" if iban else '', f"SWIFT: {swift}" if swift else ''] if p]
        if line3_parts:
            footer_lines.append(" - ".join(line3_parts))
        if extra:
            footer_lines.append(extra)

        canvas.setFont('Helvetica', 8)
        y_position = 2*cm
        for line in footer_lines:
            text_width = canvas.stringWidth(line, 'Helvetica', 8)
            x_position = (A4[0] - text_width) / 2
            canvas.drawString(x_position, y_position, line)
            y_position -= 10
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(0.5)
        canvas.line(2.0*cm, 2.5*cm, A4[0] - 2.0*cm, 2.5*cm)