"""Gmail OAuth helper for obtaining and refreshing access tokens

Usage:
  from gmail_oauth import get_gmail_access_token
  token = get_gmail_access_token(user_email)

Prerequisites:
  1. Enable Gmail API in Google Cloud project.
  2. Create OAuth Client ID (Desktop) and download client_secret JSON.
  3. Save it as gmail_credentials.json (or set GMAIL_CLIENT_SECRET_FILE env var).
  4. First run will open a browser (if possible) or provide a URL for manual auth.

Stores token in gmail_token.json (override path with GMAIL_TOKEN_FILE env var).
"""
from __future__ import annotations
import os
import json
import logging
from typing import Optional
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# Full mail scope required for SMTP XOAUTH2
SCOPES = ["https://mail.google.com/"]

DEFAULT_CLIENT_SECRET = "gmail_credentials.json"
DEFAULT_TOKEN_FILE = "gmail_token.json"


def _paths() -> tuple[Path, Path]:
    client_path = Path(os.getenv("GMAIL_CLIENT_SECRET_FILE", DEFAULT_CLIENT_SECRET)).expanduser()
    token_path = Path(os.getenv("GMAIL_TOKEN_FILE", DEFAULT_TOKEN_FILE)).expanduser()
    return client_path, token_path


def get_gmail_access_token(user_email: str) -> Optional[str]:
    """Return a valid Gmail OAuth access token or None on failure.

    Handles refresh automatically. If no token exists, runs local OAuth flow.
    """
    client_path, token_path = _paths()

    if not client_path.exists():
        logger.error(f"Gmail client secret file not found: {client_path}")
        return None

    creds: Optional[Credentials] = None

    # Load existing token
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as e:
            logger.warning(f"Failed to load existing token file: {e}")
            creds = None

    # Refresh if expired and refresh token available
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_creds(creds, token_path)
        except Exception as e:
            logger.error(f"Failed to refresh Gmail token: {e}")
            creds = None

    # If no valid creds, run flow
    if not creds or not creds.valid:
        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
            creds = flow.run_local_server(port=0, prompt='consent')
            _save_creds(creds, token_path)
        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            return None

    if not creds or not creds.valid:
        logger.error("Could not obtain valid Gmail credentials")
        return None

    if user_email and creds.token:
        return creds.token
    return None


def _save_creds(creds: Credentials, token_path: Path) -> None:
    try:
        with open(token_path, 'w', encoding='utf-8') as f:
            f.write(creds.to_json())
        logger.info(f"Saved Gmail token to {token_path}")
    except Exception as e:
        logger.error(f"Failed saving Gmail token: {e}")
