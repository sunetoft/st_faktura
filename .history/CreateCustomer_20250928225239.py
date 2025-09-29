"""
ST_Faktura Customer Management Script

This script allows users to create new customers and store them in the Google spreadsheet.
Following copilot instructions for cross-platform compatibility, proper logging, and clean architecture.

Customer data is stored in: 
https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=0#gid=0
"""

import os
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

from google_sheets_client import GoogleSheetsClient, SheetsConfig, extract_spreadsheet_id
from cvrapi_client.client import CVRApiClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('st_faktura_customers.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Customer spreadsheet configuration
CUSTOMER_SHEET_URL = "https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=0#gid=0"
CUSTOMER_SPREADSHEET_ID = extract_spreadsheet_id(CUSTOMER_SHEET_URL)
CUSTOMER_SHEET_RANGE = "A:I"  # Columns A through I for customer data (including hourly rate)


class CustomerManager:
    """
    Manages customer operations following clean architecture principles
    """
    
    def __init__(self, sheets_client: GoogleSheetsClient):
        """
        Initialize customer manager
        
        Args:
            sheets_client: Configured Google Sheets client
        """
        self.sheets_client = sheets_client
        self.spreadsheet_id = CUSTOMER_SPREADSHEET_ID
        
    def get_existing_customers(self) -> List[List[str]]:
        """
        Retrieve existing customers from the spreadsheet
        
        Returns:
            List of customer rows
        """
        try:
            logger.info("Retrieving existing customers from spreadsheet")
            customers = self.sheets_client.read_sheet(self.spreadsheet_id, CUSTOMER_SHEET_RANGE)
            logger.info(f"Found {len(customers)} existing customer records")
            return customers
        except Exception as e:
            logger.error(f"Failed to retrieve customers: {e}")
            return []
    
    def customer_id_exists(self, customer_id: str) -> bool:
        """
        Check if a customer ID already exists
        
        Args:
            customer_id: The customer ID to check
            
        Returns:
            True if customer ID exists, False otherwise
        """
        customers = self.get_existing_customers()
        
        # Skip header row if it exists
        if customers and len(customers) > 1:
            for customer in customers[1:]:
                if customer and len(customer) > 0 and customer[0] == customer_id:
                    return True
        
        return False
    
    def validate_customer_data(self, customer_data: Dict[str, str]) -> List[str]:
        """
        Validate customer data
        
        Args:
            customer_data: Dictionary containing customer information
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        required_fields = [
            'customer_id', 'company_name', 'company_address', 
            'company_cvr', 'company_zip', 'company_town', 
            'company_phone', 'company_email'
        ]
        
        for field in required_fields:
            if not customer_data.get(field, '').strip():
                errors.append(f"Missing required field: {field}")
        
        # Validate email format (basic validation)
        email = customer_data.get('company_email', '').strip()
        if email and '@' not in email:
            errors.append("Invalid email format")
        
        # Check if customer ID already exists
        customer_id = customer_data.get('customer_id', '').strip()
        if customer_id and self.customer_id_exists(customer_id):
            errors.append(f"Customer ID '{customer_id}' already exists")
        
        return errors
    
    def add_customer(self, customer_data: Dict[str, str]) -> bool:
        """
        Add a new customer to the spreadsheet
        
        Args:
            customer_data: Dictionary containing customer information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate data
            errors = self.validate_customer_data(customer_data)
            if errors:
                logger.error("Customer data validation failed:")
                for error in errors:
                    logger.error(f"  - {error}")
                return False
            
            # Prepare data for spreadsheet
            customer_row = [
                customer_data['customer_id'],
                customer_data['company_name'],
                customer_data['company_address'],
                customer_data['company_cvr'],
                customer_data['company_zip'],
                customer_data['company_town'],
                customer_data['company_phone'],
                customer_data['company_email'],
                customer_data['hourly_rate']
            ]
            
            # Add customer to spreadsheet
            logger.info(f"Adding new customer: {customer_data['customer_id']}")
            self.sheets_client.append_to_sheet(
                self.spreadsheet_id, 
                CUSTOMER_SHEET_RANGE, 
                [customer_row]
            )
            
            logger.info(f"Successfully added customer: {customer_data['company_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add customer: {e}")
            return False
    
    def setup_spreadsheet_headers(self) -> None:
        """
        Set up the spreadsheet headers if they don't exist
        """
        try:
            customers = self.get_existing_customers()
            
            # If no data or first row doesn't look like headers, add them
            headers = [
                "Customer ID", "Company Name", "Company Address", "Company CVR",
                "Company Zip", "Company Town", "Company Phone", "Company Email", "Hourly Rate (DKK)"
            ]
            
            if not customers or len(customers[0]) != len(headers):
                logger.info("Setting up spreadsheet headers")
                self.sheets_client.write_sheet(
                    self.spreadsheet_id,
                    "A1:I1",
                    [headers]
                )
                logger.info("Headers added successfully")
                
        except Exception as e:
            logger.error(f"Failed to setup headers: {e}")


def get_user_input(prompt: str, required: bool = True) -> str:
    """
    Get user input with validation
    
    Args:
        prompt: The prompt to display to the user
        required: Whether the field is required
        
    Returns:
        User input string
    """
    while True:
        value = input(f"{prompt}: ").strip()
        
        if value or not required:
            return value
        
        print("This field is required. Please enter a value.")


def get_hourly_rate() -> str:
    """
    Get hourly rate input with validation
    
    Returns:
        Hourly rate as string
    """
    while True:
        try:
            rate_input = input("Hourly Rate (DKK): ").strip()
            
            if not rate_input:
                print("This field is required. Please enter a value.")
                continue
            
            hourly_rate = float(rate_input)
            
            if hourly_rate > 0:
                return str(hourly_rate)
            else:
                print("Hourly rate must be greater than 0.")
                
        except ValueError:
            print("Please enter a valid number.")


def collect_customer_data() -> Dict[str, str]:
    """
    Collect customer data from user input
    
    Returns:
        Dictionary containing customer data
    """
    print("\n" + "="*50)
    print("ST_FAKTURA - NEW CUSTOMER REGISTRATION")
    print("="*50)
    print("Please enter the customer information:")
    print()
    
    customer_data = {}
    
    # Collect all required customer information
    customer_data['customer_id'] = get_user_input("Customer ID")
    customer_data['company_name'] = get_user_input("Company Name")
    customer_data['company_address'] = get_user_input("Company Address")
    customer_data['company_cvr'] = get_user_input("Company CVR")
    customer_data['company_zip'] = get_user_input("Company Zip Code")
    customer_data['company_town'] = get_user_input("Company Town")
    customer_data['company_phone'] = get_user_input("Company Phone")
    customer_data['company_email'] = get_user_input("Company Email")
    customer_data['hourly_rate'] = get_hourly_rate()
    
    return customer_data


def display_customer_summary(customer_data: Dict[str, str]) -> None:
    """
    Display customer data summary for confirmation
    
    Args:
        customer_data: Dictionary containing customer information
    """
    print("\n" + "="*50)
    print("CUSTOMER INFORMATION SUMMARY")
    print("="*50)
    
    print(f"Customer ID:      {customer_data['customer_id']}")
    print(f"Company Name:     {customer_data['company_name']}")
    print(f"Company Address:  {customer_data['company_address']}")
    print(f"Company CVR:      {customer_data['company_cvr']}")
    print(f"Company Zip:      {customer_data['company_zip']}")
    print(f"Company Town:     {customer_data['company_town']}")
    print(f"Company Phone:    {customer_data['company_phone']}")
    print(f"Company Email:    {customer_data['company_email']}")
    print("="*50)


def main() -> None:
    """
    Main function for customer creation
    """
    logger.info("Starting ST_Faktura Customer Creation")
    
    try:
        # Initialize Google Sheets client
        config = SheetsConfig()
        auth_method = os.getenv('AUTH_METHOD', 'service_account')
        client = GoogleSheetsClient(auth_method=auth_method, config=config)
        
        # Initialize customer manager
        customer_manager = CustomerManager(client)
        
        # Setup spreadsheet headers if needed
        customer_manager.setup_spreadsheet_headers()
        
        # Collect customer data
        customer_data = collect_customer_data()
        
        # Display summary and confirm
        display_customer_summary(customer_data)
        
        confirm = input("\nDo you want to save this customer? (y/N): ").strip().lower()
        
        if confirm == 'y':
            # Add customer to spreadsheet
            if customer_manager.add_customer(customer_data):
                print(f"\n✅ Customer '{customer_data['company_name']}' added successfully!")
                logger.info(f"Customer creation completed: {customer_data['customer_id']}")
            else:
                print(f"\n❌ Failed to add customer. Please check the logs for details.")
                sys.exit(1)
        else:
            print("\n⏭️ Customer creation cancelled.")
            logger.info("Customer creation cancelled by user")
    
    except KeyboardInterrupt:
        print("\n\n⏭️ Operation cancelled by user.")
        logger.info("Customer creation interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Unexpected error in customer creation: {e}")
        print(f"\n❌ An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()