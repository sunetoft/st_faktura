"""
Google Sheets Client for ST_Faktura Project

This module provides a simple interface to read from and write to Google Sheets
using the Google Sheets API v4.
"""

import os
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import pandas as pd

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('st_faktura_sheets.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SheetsConfig:
    """Configuration class for Google Sheets client"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        self.service_account_file = os.getenv('SERVICE_ACCOUNT_FILE', 'service_account.json')
        self.oauth_credentials_file = os.getenv('OAUTH_CREDENTIALS_FILE', 'credentials.json')
        self.oauth_token_file = os.getenv('OAUTH_TOKEN_FILE', 'token.pickle')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('SHEETS_LOG_FILE', 'st_faktura_sheets.log')


class GoogleSheetsClient:
    """
    A client for interacting with Google Sheets API
    
    This client follows clean architecture principles and provides a robust
    interface for reading from and writing to Google Sheets using the Google Sheets API v4.
    """
    
    # Scopes required for reading and writing sheets
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self, auth_method: str = "service_account", config_dir: Optional[str] = None, config: Optional[SheetsConfig] = None):
        """
        Initialize the Google Sheets client
        
        Args:
            auth_method: Either "service_account" or "oauth"
            config_dir: Directory containing credential files (defaults to current directory)
            config: Configuration object (defaults to SheetsConfig())
        """
        self.auth_method = auth_method
        self.config_dir = config_dir or os.getcwd()
        self.config = config or SheetsConfig()
        self.service = None
        self.creds = None
        
        logger.info(f"Initializing Google Sheets client with {auth_method} authentication")
        
        # Authenticate and build service
        self._authenticate()
        self._build_service()
    
    def _authenticate(self):
        """Authenticate using either service account or OAuth"""
        
        if self.auth_method == "service_account":
            self._authenticate_service_account()
        elif self.auth_method == "oauth":
            self._authenticate_oauth()
        else:
            raise ValueError("auth_method must be 'service_account' or 'oauth'")
    
    def _authenticate_service_account(self) -> None:
        """Authenticate using service account credentials"""
        service_account_file = os.path.join(
            self.config_dir, 
            self.config.service_account_file
        )
        
        if not os.path.exists(service_account_file):
            error_msg = (
                f"Service account file '{service_account_file}' not found. "
                "Please run setup_credentials.py first."
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        try:
            self.creds = ServiceAccountCredentials.from_service_account_file(
                service_account_file, scopes=self.SCOPES
            )
            logger.info("Successfully authenticated using service account")
        except Exception as e:
            logger.error(f"Failed to authenticate with service account: {e}")
            raise
    
    def _authenticate_oauth(self) -> None:
        """Authenticate using OAuth 2.0"""
        creds = None
        token_file = os.path.join(
            self.config_dir, 
            self.config.oauth_token_file
        )
        credentials_file = os.path.join(
            self.config_dir, 
            self.config.oauth_credentials_file
        )
        
        # Load existing token if available
        if os.path.exists(token_file):
            try:
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)
                logger.debug("Loaded existing OAuth token")
            except Exception as e:
                logger.warning(f"Failed to load existing token: {e}")
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed OAuth token")
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(credentials_file):
                    error_msg = (
                        f"OAuth credentials file '{credentials_file}' not found. "
                        "Please run setup_credentials.py first."
                    )
                    logger.error(error_msg)
                    raise FileNotFoundError(error_msg)
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("Obtained new OAuth credentials")
                except Exception as e:
                    logger.error(f"Failed to obtain OAuth credentials: {e}")
                    raise
            
            # Save credentials for next run
            try:
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)
                logger.debug("Saved OAuth token for future use")
            except Exception as e:
                logger.warning(f"Failed to save token: {e}")
        
        self.creds = creds
        logger.info("Successfully authenticated using OAuth 2.0")
    
    def _build_service(self) -> None:
        """Build the Google Sheets API service"""
        try:
            self.service = build('sheets', 'v4', credentials=self.creds)
            logger.info("Google Sheets API service ready")
        except Exception as e:
            error_msg = f"Failed to build Google Sheets service: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def read_sheet(self, spreadsheet_id: str, range_name: str = "A:Z") -> List[List[str]]:
        """
        Read data from a Google Sheet
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            range_name: The range to read (e.g., "A1:E10", "Sheet1!A:Z")
        
        Returns:
            List of rows, where each row is a list of cell values
        
        Raises:
            HttpError: If there's an error accessing the Google Sheet
        """
        try:
            logger.debug(f"Reading sheet {spreadsheet_id}, range: {range_name}")
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            logger.info(f"Successfully read {len(values)} rows from sheet")
            return values
            
        except HttpError as error:
            error_msg = f"Error reading sheet: {error}"
            logger.error(error_msg)
            raise
    
    def read_sheet_as_dataframe(self, spreadsheet_id: str, range_name: str = "A:Z", 
                               header_row: int = 0) -> pd.DataFrame:
        """
        Read data from a Google Sheet and return as pandas DataFrame
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            range_name: The range to read
            header_row: Row index to use as column headers (0-based)
        
        Returns:
            pandas DataFrame
        """
        values = self.read_sheet(spreadsheet_id, range_name)
        
        if not values:
            return pd.DataFrame()
        
        if len(values) > header_row:
            df = pd.DataFrame(values[header_row + 1:], columns=values[header_row])
        else:
            df = pd.DataFrame(values)
        
        return df
    
    def write_sheet(self, spreadsheet_id: str, range_name: str, 
                   values: List[List[Any]], value_input_option: str = "RAW") -> Dict[str, Any]:
        """
        Write data to a Google Sheet
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            range_name: The range to write to (e.g., "A1:E10", "Sheet1!A1")
            values: 2D list of values to write
            value_input_option: How to interpret the data ("RAW" or "USER_ENTERED")
            
        Returns:
            Dictionary containing the API response
            
        Raises:
            HttpError: If there's an error writing to the Google Sheet
        """
        try:
            logger.debug(f"Writing to sheet {spreadsheet_id}, range: {range_name}, rows: {len(values)}")
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body
            ).execute()
            
            updated_cells = result.get('updatedCells', 0)
            logger.info(f"Successfully updated {updated_cells} cells in sheet")
            return result
            
        except HttpError as error:
            error_msg = f"Error writing to sheet: {error}"
            logger.error(error_msg)
            raise
    
    def write_dataframe_to_sheet(self, spreadsheet_id: str, range_name: str, 
                                df: pd.DataFrame, include_header: bool = True) -> Dict[str, Any]:
        """
        Write a pandas DataFrame to a Google Sheet
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            range_name: The range to write to
            df: pandas DataFrame to write
            include_header: Whether to include column headers
            
        Returns:
            Dictionary containing the API response
        """
        logger.debug(f"Writing DataFrame to sheet {spreadsheet_id}, shape: {df.shape}")
        values = []
        
        if include_header:
            values.append(df.columns.tolist())
        
        # Convert DataFrame to list of lists
        for _, row in df.iterrows():
            values.append(row.tolist())
        
        return self.write_sheet(spreadsheet_id, range_name, values)
    
    def append_to_sheet(self, spreadsheet_id: str, range_name: str, 
                       values: List[List[Any]], value_input_option: str = "RAW") -> Dict[str, Any]:
        """
        Append data to a Google Sheet
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            range_name: The range to append to
            values: 2D list of values to append
            value_input_option: How to interpret the data
            
        Returns:
            Dictionary containing the API response
            
        Raises:
            HttpError: If there's an error appending to the Google Sheet
        """
        try:
            logger.debug(f"Appending to sheet {spreadsheet_id}, range: {range_name}, rows: {len(values)}")
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body
            ).execute()
            
            updated_cells = result.get('updates', {}).get('updatedCells', 0)
            logger.info(f"Successfully appended {updated_cells} cells to sheet")
            return result
            
        except HttpError as error:
            error_msg = f"Error appending to sheet: {error}"
            logger.error(error_msg)
            raise
    
    def clear_sheet(self, spreadsheet_id: str, range_name: str) -> Dict[str, Any]:
        """
        Clear data from a Google Sheet range
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            range_name: The range to clear
            
        Returns:
            Dictionary containing the API response
            
        Raises:
            HttpError: If there's an error clearing the Google Sheet
        """
        try:
            logger.debug(f"Clearing sheet {spreadsheet_id}, range: {range_name}")
            result = self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            logger.info(f"Successfully cleared range {range_name}")
            return result
            
        except HttpError as error:
            error_msg = f"Error clearing sheet: {error}"
            logger.error(error_msg)
            raise
    
    def get_sheet_info(self, spreadsheet_id: str) -> Dict[str, Any]:
        """
        Get information about the spreadsheet
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            
        Returns:
            Dictionary with spreadsheet metadata including title, sheets, and ID
            
        Raises:
            HttpError: If there's an error accessing the Google Sheet
        """
        try:
            logger.debug(f"Getting info for sheet {spreadsheet_id}")
            result = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            title = result.get('properties', {}).get('title', 'Unknown')
            sheets = [sheet['properties']['title'] for sheet in result.get('sheets', [])]
            
            info = {
                'title': title,
                'sheets': sheets,
                'spreadsheet_id': spreadsheet_id
            }
            
            logger.info(f"Retrieved sheet info: {title} with {len(sheets)} sheets")
            return info
            
        except HttpError as error:
            error_msg = f"Error getting sheet info: {error}"
            logger.error(error_msg)
            raise


def extract_spreadsheet_id(url: str) -> str:
    """
    Extract spreadsheet ID from a Google Sheets URL
    
    Args:
        url: Google Sheets URL
        
    Returns:
        Spreadsheet ID
    """
    if '/spreadsheets/d/' in url:
        return url.split('/spreadsheets/d/')[1].split('/')[0]
    else:
        # Assume it's already an ID
        return url