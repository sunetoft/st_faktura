"""
Google Sheets API Credentials Setup Helper

This script helps you set up authentication for Google Sheets API.
Following copilot instructions for cross-platform compatibility and proper logging.

You have two options:
1. Service Account (recommended for server applications)
2. OAuth 2.0 (for user applications)

Before running this script:
1. Go to Google Cloud Console (https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable Google Sheets API
4. Create credentials (Service Account or OAuth 2.0)
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_service_account():
    """
    Setup instructions for Service Account authentication
    """
    print("\n=== SERVICE ACCOUNT SETUP ===")
    print("1. Go to Google Cloud Console: https://console.cloud.google.com")
    print("2. Select your project or create a new one")
    print("3. Go to 'APIs & Services' > 'Credentials'")
    print("4. Click 'Create Credentials' > 'Service Account'")
    print("5. Fill in the service account details")
    print("6. Go to the created service account and create a JSON key")
    print("7. Download the JSON file and place it in this project folder")
    print("8. Rename it to 'service_account.json'")
    print("9. Share your Google Sheet with the service account email")
    print("   (found in the JSON file as 'client_email')")
    
    # Check if service account file exists
    service_account_path = Path("service_account.json")
    if service_account_path.exists():
        print(f"\n✅ Found service account file: {service_account_path}")
        try:
            with open(service_account_path, 'r') as f:
                creds = json.load(f)
                print(f"📧 Service account email: {creds.get('client_email', 'Not found')}")
                print("\nMake sure to share your Google Sheet with this email address!")
        except Exception as e:
            print(f"❌ Error reading service account file: {e}")
    else:
        print(f"\n❌ Service account file not found: {service_account_path}")
        print("Please download and place your service account JSON file here.")

def setup_oauth():
    """
    Setup instructions for OAuth 2.0 authentication
    """
    print("\n=== OAUTH 2.0 SETUP ===")
    print("1. Go to Google Cloud Console: https://console.cloud.google.com")
    print("2. Select your project or create a new one")
    print("3. Go to 'APIs & Services' > 'Credentials'")
    print("4. Click 'Create Credentials' > 'OAuth 2.0 Client ID'")
    print("5. Select 'Desktop Application'")
    print("6. Download the JSON file and place it in this project folder")
    print("7. Rename it to 'credentials.json'")
    
    # Check if OAuth credentials file exists
    oauth_path = Path("credentials.json")
    if oauth_path.exists():
        print(f"\n✅ Found OAuth credentials file: {oauth_path}")
    else:
        print(f"\n❌ OAuth credentials file not found: {oauth_path}")
        print("Please download and place your OAuth 2.0 credentials JSON file here.")

def main():
    print("Google Sheets API Authentication Setup")
    print("=====================================")
    
    print("\nWhich authentication method would you like to use?")
    print("1. Service Account (recommended for automated scripts)")
    print("2. OAuth 2.0 (for user-interactive applications)")
    
    choice = input("\nEnter your choice (1 or 2): ").strip()
    
    if choice == "1":
        setup_service_account()
    elif choice == "2":
        setup_oauth()
    else:
        print("Invalid choice. Please run the script again and choose 1 or 2.")
        return
    
    print("\n" + "="*50)
    print("After setting up credentials, you can run the main script!")

if __name__ == "__main__":
    main()