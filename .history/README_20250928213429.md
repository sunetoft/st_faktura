# ST_Faktura - Complete Invoice Management System

This project provides a comprehensive invoice management system with Google Sheets integration for the ST_Faktura application.

**Developed following copilot instructions for cross-platform compatibility, clean architecture, proper logging, and deployment readiness.**

## 🎯 System Overview

ST_Faktura is a complete invoice management solution that includes:
- **Customer Management** - Add and manage customer information
- **Task Tracking** - Record billable tasks and time
- **Invoice Generation** - Create professional PDF invoices
- **Email Integration** - Send invoices directly to customers
- **Google Sheets Integration** - All data synchronized with Google Sheets

## 📋 Features

### Core Invoice Management
- ✅ **Customer Management** - Add, store, and manage customer details
- ✅ **Task Creation** - Record billable tasks with time tracking
- ✅ **Professional PDF Invoices** - Generate invoices with consecutive numbering
- ✅ **Email Integration** - Send invoices directly to customers
- ✅ **Company Details Management** - Configure your business information

### Technical Features  
- ✅ **Cross-platform compatibility** (Windows, Linux, macOS)
- ✅ **Proper logging** with configurable levels and file output
- ✅ **Environment-based configuration** using .env files
- ✅ **Type hints** and Pythonic patterns throughout
- ✅ **Clean architecture** with separation of concerns
- ✅ **Google Sheets API integration** for data storage
- ✅ **PDF generation** with ReportLab
- ✅ **AWS EC2 + Nginx deployment ready**

## 🚀 Scripts Overview

### 1. CreateCustomer.py
Creates new customers and stores them in Google Sheets.

**Usage:**
```bash
python CreateCustomer.py
```

**Collects:**
- Customer ID, Company Name, Address, CVR
- Zip Code, Town, Phone, Email

### 2. CreateTask.py  
Creates billable tasks associated with customers.

**Usage:**
```bash
python CreateTask.py
```

**Features:**
- Select customer from existing customers
- Choose task type from predefined types
- Add task description and time (minutes)
- Automatic date stamping

### 3. CreateInvoice.py
Generates professional PDF invoices from tasks.

**Usage:**
```bash
python CreateInvoice.py
```

**Features:**
- Select customer and their tasks
- Calculate total time and amount
- Generate PDF with consecutive numbering (starts from 785)
- Email invoice to customer automatically
- 8-day payment terms

### 4. Tool_MyCompanyDetails.py
Manages your company information for invoices.

**Usage:**
```bash
python Tool_MyCompanyDetails.py
```

**Configures:**
- Company details (name, address, CVR, etc.)
- Banking information (IBAN, SWIFT, account details)

## 📊 Google Sheets Integration

The system uses three Google Sheets:

1. **Customers Sheet** (gid=0)
   - Customer ID, Company Name, Address, CVR, Zip, Town, Phone, Email

2. **Task Types Sheet** (gid=288943747)  
   - Predefined task types for selection

3. **Tasks Sheet** (gid=1276274497)
   - Date, Customer Name, Task Type, Description, Time (Minutes)

## 🚀 Quick Start

### 1. Install Dependencies

The required packages are already installed in your virtual environment:
- `google-api-python-client`
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `pandas`
- `python-dotenv`

### 2. Configure Environment

Create your environment configuration:

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your preferences
# nano .env  # On Linux/macOS
# notepad .env  # On Windows
```

### 3. Set Up Authentication

Run the setup script to configure authentication:

```bash
python setup_credentials.py
```

Choose between:
- **Service Account** (recommended for automated scripts and server deployments)
- **OAuth 2.0** (for user-interactive applications)

### 3. Configure Google Cloud Console

#### For Service Account:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable Google Sheets API
4. Go to "APIs & Services" > "Credentials"
5. Create "Service Account" credentials
6. Download the JSON key file
7. Rename it to `service_account.json` and place in project folder
8. **Important**: Share your Google Sheet with the service account email (found in the JSON file)

#### For OAuth 2.0:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable Google Sheets API
4. Go to "APIs & Services" > "Credentials"
5. Create "OAuth 2.0 Client ID" for Desktop Application
6. Download the JSON file
7. Rename it to `credentials.json` and place in project folder

### 4. Run the Example

```bash
python st_faktura_sheets.py
```

## 📖 Usage Examples

### Basic Reading

```python
from google_sheets_client import GoogleSheetsClient

# Initialize client
client = GoogleSheetsClient(auth_method="service_account")

# Your sheet ID (extracted from URL)
sheet_id = "170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0"

# Read data
data = client.read_sheet(sheet_id, "A:Z")
print(f"Read {len(data)} rows")

# Read as DataFrame
df = client.read_sheet_as_dataframe(sheet_id, "A:Z")
print(df.head())
```

### Writing Data

```python
# Write raw data
data_to_write = [
    ["Name", "Age", "City"],
    ["John", "25", "New York"],
    ["Jane", "30", "Los Angeles"]
]
client.write_sheet(sheet_id, "A1:C3", data_to_write)

# Write DataFrame
import pandas as pd
df = pd.DataFrame({
    'Name': ['Alice', 'Bob'],
    'Age': [28, 35],
    'City': ['Chicago', 'Miami']
})
client.write_dataframe_to_sheet(sheet_id, "A1", df, include_header=True)
```

### Appending Data

```python
# Append new rows
new_data = [
    ["Charlie", "40", "Seattle"],
    ["Diana", "22", "Boston"]
]
client.append_to_sheet(sheet_id, "A:C", new_data)
```

## 🔧 API Reference

### GoogleSheetsClient Class

#### Constructor
```python
GoogleSheetsClient(auth_method="service_account")
```
- `auth_method`: Either "service_account" or "oauth"

#### Methods

**`read_sheet(spreadsheet_id, range_name="A:Z")`**
- Read data from sheet
- Returns: List of lists (rows and cells)

**`read_sheet_as_dataframe(spreadsheet_id, range_name="A:Z", header_row=0)`**
- Read data as pandas DataFrame
- Returns: pandas DataFrame

**`write_sheet(spreadsheet_id, range_name, values, value_input_option="RAW")`**
- Write data to sheet
- `values`: 2D list of data to write

**`write_dataframe_to_sheet(spreadsheet_id, range_name, df, include_header=True)`**
- Write pandas DataFrame to sheet

**`append_to_sheet(spreadsheet_id, range_name, values, value_input_option="RAW")`**
- Append data to sheet

**`clear_sheet(spreadsheet_id, range_name)`**
- Clear data from range

**`get_sheet_info(spreadsheet_id)`**
- Get sheet metadata

### Utility Functions

**`extract_spreadsheet_id(url)`**
- Extract spreadsheet ID from Google Sheets URL

## 📁 Project Structure

```
ST_Faktura/
├── venv/                          # Python virtual environment
├── google_sheets_client.py        # Main Google Sheets client class
├── st_faktura_sheets.py           # Example usage script
├── setup_credentials.py           # Authentication setup helper  
├── service_account.json           # Service account credentials (you create this)
├── credentials.json               # OAuth credentials (you create this)
├── token.pickle                   # OAuth token cache (auto-generated)
├── .gitignore                     # Git ignore file
└── README.md                      # This file
```

## 🔒 Security Notes

- **Never commit credential files** (`service_account.json`, `credentials.json`, `token.pickle`) to version control
- The `.gitignore` file is configured to exclude these files
- Service account email must have access to your Google Sheet
- OAuth requires user consent for first-time access

## 🎯 Your Specific Google Sheet

Your sheet URL: `https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=0#gid=0`

Spreadsheet ID: `170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0`

## 🚨 Important Reminders

1. **Share your sheet** with the service account email (found in `service_account.json`)
2. **Enable Google Sheets API** in Google Cloud Console
3. **Test with read-only operations** first before writing data
4. **Backup your sheet** before running write operations

## 🔧 Troubleshooting

### Common Issues

**"Service account file not found"**
- Run `python setup_credentials.py`
- Download credentials from Google Cloud Console
- Place the file in the project folder with correct name

**"Permission denied" or "403 Forbidden"**
- Make sure you've shared the Google Sheet with the service account email
- Check that Google Sheets API is enabled in Google Cloud Console

**"Invalid authentication"**
- For OAuth: Delete `token.pickle` and re-authenticate
- For Service Account: Re-download the JSON file

**"Sheet not found"**
- Verify the spreadsheet ID is correct
- Make sure the sheet is accessible with your credentials

## 📞 Support

If you encounter issues:
1. Check the error messages for specific guidance
2. Verify your Google Cloud Console setup
3. Ensure proper sheet sharing permissions
4. Test with the read-only example first

---

**Happy coding with ST_Faktura! 🎉**