# ST_Faktura Google Sheets Integration

This project provides a Python interface to read from and write to Google Sheets for the ST_Faktura application.

## 📋 Features

- ✅ Read data from Google Sheets
- ✅ Write data to Google Sheets
- ✅ Append new rows to sheets
- ✅ Clear sheet ranges
- ✅ Pandas DataFrame integration
- ✅ Support for both Service Account and OAuth authentication
- ✅ Easy-to-use Python classes and methods

## 🚀 Quick Start

### 1. Install Dependencies

The required packages are already installed in your virtual environment:
- `google-api-python-client`
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `pandas`

### 2. Set Up Authentication

Run the setup script to configure authentication:

```bash
python setup_credentials.py
```

Choose between:
- **Service Account** (recommended for automated scripts)
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