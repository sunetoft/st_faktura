"""
Test script for the new ST Digital invoice template

This script generates a sample invoice to test the new template design.
"""

import os
import sys
from datetime import datetime
from invoice_utils import InvoicePDFGenerator, InvoiceNumberManager

# Sample data for testing
SAMPLE_COMPANY_DETAILS = {
    'company_name': 'ST Digital',
    'company_address': 'Baldersgade 69 2 th',
    'company_zip': '2200',
    'company_town': 'Kbh. N.',
    'company_cvr': '18194104',
    'company_phone': '29439585',
    'company_email': 'sure@stdigital.dk',
    'bank_name': 'Bank Nordik',
    'bank_account': '6506 / 3061152279',
    'iban': 'DK9165063061152279',
    'swift': 'BANCDKKK'
}

SAMPLE_CUSTOMER_DETAILS = {
    'id': 'KDK001',
    'name': 'KDK ApS',
    'address': 'Sofiegade 2, 4. sal Kbh K',
    'zip': '1418',
    'town': 'København K',
    'cvr': 'DK12345678',
    'phone': '12345678',
    'email': 'test@kdk.dk'
}

SAMPLE_TASKS = [
    {
        'date': '2025-09-01',
        'customer_name': 'KDK ApS',
        'tasktype': 'Hosting',
        'description': 'Website hosting - Staerkere.com (1.2.25 - 31.1.26 halvpart)',
        'time_minutes': '60'
    },
    {
        'date': '2025-09-15',
        'customer_name': 'KDK ApS',
        'tasktype': 'Konsultation',
        'description': 'Email setup og konfiguration',
        'time_minutes': '30'
    }
]

def test_invoice_generation():
    """Test the new invoice template"""
    print("Testing ST Digital Invoice Template")
    print("=" * 40)
    
    try:
        # Initialize generators
        pdf_generator = InvoicePDFGenerator()
        number_manager = InvoiceNumberManager()
        
        # Generate test invoice
        print("Generating test invoice...")
        
        pdf_path = pdf_generator.generate_invoice_pdf(
            invoice_number=783,  # Match the template
            company_details=SAMPLE_COMPANY_DETAILS,
            customer_details=SAMPLE_CUSTOMER_DETAILS,
            tasks=SAMPLE_TASKS,
            hourly_rate=300.0  # Match template rate
        )
        
        print(f"✅ Test invoice generated successfully!")
        print(f"📄 File location: {pdf_path}")
        print(f"📁 Full path: {os.path.abspath(pdf_path)}")
        
        # Check if file exists and get size
        if os.path.exists(pdf_path):
            file_size = os.path.getsize(pdf_path)
            print(f"📊 File size: {file_size:,} bytes")
        
        return pdf_path
        
    except Exception as e:
        print(f"❌ Error generating test invoice: {e}")
        return None

if __name__ == "__main__":
    test_invoice_generation()