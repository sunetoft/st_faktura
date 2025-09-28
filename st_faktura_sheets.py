"""
Example usage of Google Sheets Client for ST_Faktura Project

This script demonstrates how to read from and write to your specific Google Sheet:
https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=0#gid=0

Following the copilot instructions for cross-platform compatibility, proper logging,
and clean architecture patterns.
"""

import os
import logging
from typing import Tuple, Optional
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from google_sheets_client import GoogleSheetsClient, SheetsConfig, extract_spreadsheet_id

# Load environment variables
load_dotenv()

# Configure logging for this script
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Your Google Sheet URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=0#gid=0"
SPREADSHEET_ID = extract_spreadsheet_id(SHEET_URL)

def main() -> None:
    """
    Main function demonstrating Google Sheets operations
    
    This function follows the copilot instructions for proper error handling,
    logging, and clean architecture patterns.
    """
    
    logger.info("ST_Faktura Google Sheets Integration")
    logger.info("===================================")
    logger.info(f"Working with sheet: {SHEET_URL}")
    logger.info(f"Spreadsheet ID: {SPREADSHEET_ID}")
    
    try:
        # Initialize configuration and client
        logger.info("1. Initializing Google Sheets client...")
        config = SheetsConfig()
        auth_method = os.getenv('AUTH_METHOD', 'service_account')
        client = GoogleSheetsClient(auth_method=auth_method, config=config)
        
        # Get sheet information
        print("\n2. Getting sheet information...")
        sheet_info = client.get_sheet_info(SPREADSHEET_ID)
        print(f"📊 Sheet title: {sheet_info['title']}")
        print(f"📋 Available sheets: {', '.join(sheet_info['sheets'])}")
        
        # Read all data from the sheet
        print("\n3. Reading data from sheet...")
        data = client.read_sheet(SPREADSHEET_ID, "A:Z")  # Read all columns
        
        if data:
            print(f"📄 Found {len(data)} rows of data")
            print("First few rows:")
            for i, row in enumerate(data[:5]):  # Show first 5 rows
                print(f"  Row {i+1}: {row}")
        else:
            print("📄 No data found in sheet")
        
        # Read data as pandas DataFrame
        print("\n4. Reading data as DataFrame...")
        df = client.read_sheet_as_dataframe(SPREADSHEET_ID, "A:Z")
        
        if not df.empty:
            print(f"📊 DataFrame shape: {df.shape}")
            print("DataFrame info:")
            print(df.info())
            print("\nFirst few rows:")
            print(df.head())
        else:
            print("📊 Empty DataFrame")
        
        # Example: Writing data to the sheet
        print("\n5. Writing example data...")
        
        # Example data to write
        example_data = [
            ["Timestamp", "Item", "Quantity", "Price", "Total"],
            [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Sample Item", "1", "100.00", "100.00"],
            [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Another Item", "2", "50.00", "100.00"]
        ]
        
        # Write to a specific range (adjust as needed)
        # Be careful not to overwrite important data!
        write_range = "A1:E3"  # Adjust this range as needed
        
        confirmation = input(f"Write example data to range {write_range}? (y/N): ")
        if confirmation.lower() == 'y':
            client.write_sheet(SPREADSHEET_ID, write_range, example_data)
            print("✅ Example data written to sheet")
        else:
            print("⏭️ Skipped writing data")
        
        # Example: Appending data
        print("\n6. Appending data example...")
        
        new_row = [
            [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Appended Item", "3", "25.00", "75.00"]
        ]
        
        confirmation = input("Append a new row to the sheet? (y/N): ")
        if confirmation.lower() == 'y':
            client.append_to_sheet(SPREADSHEET_ID, "A:E", new_row)
            print("✅ New row appended to sheet")
        else:
            print("⏭️ Skipped appending data")
        
        # Example: Working with DataFrame
        print("\n7. DataFrame operations example...")
        
        # Create a sample DataFrame
        sample_df = pd.DataFrame({
            'Date': [datetime.now().strftime("%Y-%m-%d")],
            'Product': ['Sample Product'],
            'Quantity': [5],
            'Unit_Price': [20.00],
            'Total': [100.00]
        })
        
        print("Sample DataFrame:")
        print(sample_df)
        
        confirmation = input("Write this DataFrame to the sheet? (y/N): ")
        if confirmation.lower() == 'y':
            # Write DataFrame to sheet (starting from row 10 to avoid overwriting)
            client.write_dataframe_to_sheet(SPREADSHEET_ID, "A10", sample_df, include_header=True)
            print("✅ DataFrame written to sheet")
        else:
            print("⏭️ Skipped writing DataFrame")
        
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("Please run 'python setup_credentials.py' first to set up authentication.")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you have proper access to the Google Sheet and correct credentials.")

def read_only_example():
    """Example of reading data only (safer for testing)"""
    
    print("ST_Faktura Google Sheets - Read Only Example")
    print("===========================================")
    
    try:
        client = GoogleSheetsClient(auth_method="service_account")
        
        # Read data
        data = client.read_sheet(SPREADSHEET_ID, "A:Z")
        df = client.read_sheet_as_dataframe(SPREADSHEET_ID, "A:Z")
        
        print(f"📄 Raw data: {len(data)} rows")
        print(f"📊 DataFrame: {df.shape}")
        
        # Display some statistics if data exists
        if not df.empty:
            print("\nDataFrame summary:")
            print(df.describe())
        
        return data, df
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None

if __name__ == "__main__":
    print("Choose an option:")
    print("1. Full example (read and write)")
    print("2. Read-only example (safer for testing)")
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "1":
        main()
    elif choice == "2":
        read_only_example()
    else:
        print("Invalid choice. Running read-only example...")
        read_only_example()