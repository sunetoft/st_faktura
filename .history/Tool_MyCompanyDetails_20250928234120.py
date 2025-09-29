"""
ST_Faktura Company Details Management Script

This script allows users to set up and manage company information that will be
used on invoices and other business documents.

Following copilot instructions for cross-platform compatibility, proper logging, and clean architecture.
"""

import os
import json
import logging
import sys
from typing import Dict, Optional
from dotenv import load_dotenv
from google_sheets_client import GoogleSheetsClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('st_faktura_company.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Company details file path (cross-platform)
COMPANY_DETAILS_FILE = os.path.join(os.getcwd(), 'st-faktura.json')

# Google Sheets configuration
SPREADSHEET_ID = "170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0"
COMPANY_SHEET_RANGE = "Company Details!A:N"  # Assuming columns A-N for all company data


class CompanyDetailsManager:
    """
    Manages company details following clean architecture principles
    """
    
    def __init__(self, config_file: str = COMPANY_DETAILS_FILE):
        """
        Initialize company details manager
        
        Args:
            config_file: Path to the company details configuration file
        """
        self.config_file = config_file
        self.sheets_client = GoogleSheetsClient()
        self.spreadsheet_id = SPREADSHEET_ID
        
    def load_company_details(self) -> Optional[Dict[str, str]]:
        """
        Load existing company details from file
        
        Returns:
            Dictionary containing company details or None if not found
        """
        try:
            if os.path.exists(self.config_file):
                logger.info(f"Loading company details from {self.config_file}")
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    company_details = json.load(f)
                logger.info("Company details loaded successfully")
                return company_details
            else:
                logger.info("No existing company details file found")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load company details: {e}")
            return None
    
    def save_company_details(self, company_details: Dict[str, str]) -> bool:
        """
        Save company details to file
        
        Args:
            company_details: Dictionary containing company information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Saving company details to {self.config_file}")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(company_details, f, indent=2, ensure_ascii=False)
            
            logger.info("Company details saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save company details: {e}")
            return False
    
    def validate_company_details(self, company_details: Dict[str, str]) -> list:
        """
        Validate company details
        
        Args:
            company_details: Dictionary containing company information
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        required_fields = [
            'company_name', 'company_address', 'company_cvr', 
            'company_zip', 'company_town', 'company_phone', 
            'company_email', 'bank_name', 'bank_account', 'iban', 'swift'
        ]
        
        for field in required_fields:
            if not company_details.get(field, '').strip():
                errors.append(f"Missing required field: {field}")
        
        # Validate email format (basic validation)
        email = company_details.get('company_email', '').strip()
        if email and '@' not in email:
            errors.append("Invalid email format")
        
        return errors
    
    def save_to_google_sheets(self, company_details: Dict[str, str]) -> bool:
        """
        Save company details to Google Sheets
        
        Args:
            company_details: Dictionary containing company information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Saving company details to Google Sheets")
            
            # Set up headers if needed
            self.setup_company_sheet_headers()
            
            # Prepare company data row
            company_row = [
                company_details['company_name'],
                company_details['company_address'],
                company_details['company_cvr'],
                company_details['company_zip'],
                company_details['company_town'],
                company_details['company_phone'],
                company_details['company_email'],
                company_details['bank_name'],
                company_details['bank_account'],
                company_details['iban'],
                company_details['swift'],
                company_details.get('additional_info', '')
            ]
            
            # Check if company already exists and update, or append new
            existing_data = self.sheets_client.read_sheet(self.spreadsheet_id, COMPANY_SHEET_RANGE)
            
            if existing_data and len(existing_data) > 1:
                # Update existing row (assume row 2 is the data row)
                logger.info("Updating existing company details in sheet")
                self.sheets_client.write_sheet(
                    self.spreadsheet_id,
                    "Company Details!A2:L2",
                    [company_row]
                )
            else:
                # Append new row
                logger.info("Adding new company details to sheet")
                self.sheets_client.append_to_sheet(
                    self.spreadsheet_id,
                    COMPANY_SHEET_RANGE,
                    [company_row]
                )
            
            logger.info("Company details saved to Google Sheets successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save company details to Google Sheets: {e}")
            return False
    
    def setup_company_sheet_headers(self) -> None:
        """
        Set up the company sheet headers if they don't exist
        """
        try:
            logger.info("Checking company sheet headers")
            existing_data = self.sheets_client.read_sheet(self.spreadsheet_id, COMPANY_SHEET_RANGE)
            
            headers = [
                "Company Name", "Address", "CVR", "Zip Code", "Town", "Phone", 
                "Email", "Bank Name", "Bank Account", "IBAN", "SWIFT", "Additional Information"
            ]
            
            # If no data or headers don't match, set them up
            if not existing_data or len(existing_data[0]) != len(headers):
                logger.info("Setting up company sheet headers")
                self.sheets_client.write_sheet(
                    self.spreadsheet_id,
                    "Company Details!A1:L1",
                    [headers]
                )
                logger.info("Company headers added successfully")
                
        except Exception as e:
            logger.error(f"Failed to setup company headers: {e}")


def get_user_input(prompt: str, current_value: str = "", required: bool = True) -> str:
    """
    Get user input with validation and current value display
    
    Args:
        prompt: The prompt to display to the user
        current_value: Current value to display in brackets
        required: Whether the field is required
        
    Returns:
        User input string
    """
    while True:
        display_prompt = prompt
        if current_value:
            display_prompt += f" [{current_value}]"
        display_prompt += ": "
        
        value = input(display_prompt).strip()
        
        # If no input provided, use current value
        if not value and current_value:
            return current_value
        
        if value or not required:
            return value
        
        print("This field is required. Please enter a value.")


def collect_company_details(existing_details: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Collect company details from user input
    
    Args:
        existing_details: Existing company details to use as defaults
        
    Returns:
        Dictionary containing company data
    """
    if existing_details:
        print("\n" + "="*60)
        print("UPDATING EXISTING COMPANY DETAILS")
        print("="*60)
        print("Press Enter to keep current values, or type new values:")
    else:
        print("\n" + "="*60)
        print("ST_FAKTURA - COMPANY DETAILS SETUP")
        print("="*60)
        print("Please enter your company information:")
    
    print()
    
    current = existing_details or {}
    company_details = {}
    
    # Collect all required company information
    company_details['company_name'] = get_user_input(
        "Company Name", current.get('company_name', '')
    )
    company_details['company_address'] = get_user_input(
        "Company Address", current.get('company_address', '')
    )
    company_details['company_cvr'] = get_user_input(
        "Company CVR", current.get('company_cvr', '')
    )
    company_details['company_zip'] = get_user_input(
        "Company Zip Code", current.get('company_zip', '')
    )
    company_details['company_town'] = get_user_input(
        "Company Town", current.get('company_town', '')
    )
    company_details['company_phone'] = get_user_input(
        "Company Phone", current.get('company_phone', '')
    )
    company_details['company_email'] = get_user_input(
        "Company Email", current.get('company_email', '')
    )
    
    # Banking information
    print("\n--- Banking Information ---")
    company_details['bank_name'] = get_user_input(
        "Bank Name", current.get('bank_name', '')
    )
    company_details['bank_account'] = get_user_input(
        "Bank Account Number", current.get('bank_account', '')
    )
    company_details['iban'] = get_user_input(
        "IBAN Number", current.get('iban', '')
    )
    company_details['swift'] = get_user_input(
        "SWIFT Code", current.get('swift', '')
    )
    
    # Additional information
    print("\n--- Additional Information ---")
    company_details['additional_info'] = get_user_input(
        "Additional Information", current.get('additional_info', ''), required=False
    )
    
    return company_details


def display_company_summary(company_details: Dict[str, str]) -> None:
    """
    Display company details summary for confirmation
    
    Args:
        company_details: Dictionary containing company information
    """
    print("\n" + "="*60)
    print("COMPANY INFORMATION SUMMARY")
    print("="*60)
    
    print(f"Company Name:     {company_details['company_name']}")
    print(f"Company Address:  {company_details['company_address']}")
    print(f"Company CVR:      {company_details['company_cvr']}")
    print(f"Company Zip:      {company_details['company_zip']}")
    print(f"Company Town:     {company_details['company_town']}")
    print(f"Company Phone:    {company_details['company_phone']}")
    print(f"Company Email:    {company_details['company_email']}")
    
    print("\n--- Banking Information ---")
    print(f"Bank Name:        {company_details['bank_name']}")
    print(f"Bank Account:     {company_details['bank_account']}")
    print(f"IBAN:             {company_details['iban']}")
    print(f"SWIFT:            {company_details['swift']}")
    
    print("\n--- Additional Information ---")
    print(f"Additional Info:  {company_details.get('additional_info', 'N/A')}")
    print("="*60)


def main() -> None:
    """
    Main function for company details management
    """
    logger.info("Starting ST_Faktura Company Details Management")
    
    try:
        # Initialize company details manager
        company_manager = CompanyDetailsManager()
        
        # Load existing details if available
        existing_details = company_manager.load_company_details()
        
        if existing_details:
            print(f"\n✅ Found existing company details in {COMPANY_DETAILS_FILE}")
            display_company_summary(existing_details)
            
            update_choice = input("\nDo you want to update these details? (y/N): ").strip().lower()
            if update_choice != 'y':
                print("\n⏭️ Company details management cancelled.")
                return
        
        # Collect company details
        company_details = collect_company_details(existing_details)
        
        # Validate details
        errors = company_manager.validate_company_details(company_details)
        if errors:
            print("\n❌ Validation errors found:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        
        # Display summary and confirm
        display_company_summary(company_details)
        
        confirm = input("\nDo you want to save these company details? (y/N): ").strip().lower()
        
        if confirm == 'y':
            # Save company details to both local file and Google Sheets
            local_saved = company_manager.save_company_details(company_details)
            sheets_saved = company_manager.save_to_google_sheets(company_details)
            
            if local_saved and sheets_saved:
                print(f"\n✅ Company details saved successfully!")
                print(f"File location: {COMPANY_DETAILS_FILE}")
                print(f"Google Sheets: Updated successfully")
                logger.info("Company details management completed successfully")
            elif local_saved:
                print(f"\n⚠️ Company details saved to local file but failed to save to Google Sheets.")
                print(f"File location: {COMPANY_DETAILS_FILE}")
                print(f"Please check the logs for Google Sheets error details.")
                logger.warning("Company details saved locally but not to Google Sheets")
            else:
                print(f"\n❌ Failed to save company details. Please check the logs for details.")
                sys.exit(1)
        else:
            print("\n⏭️ Company details save cancelled.")
            logger.info("Company details save cancelled by user")
    
    except KeyboardInterrupt:
        print("\n\n⏭️ Operation cancelled by user.")
        logger.info("Company details management interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Unexpected error in company details management: {e}")
        print(f"\n❌ An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()