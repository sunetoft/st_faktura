"""Replace the Drive copy of an invoice PDF in place (same fileId, same name).

Usage: python3 replace_drive_invoice_pdf.py 836
"""
import hashlib
import io
import os
import sys

sys.path.insert(0, "/opt/st_faktura")
os.chdir("/opt/st_faktura")

from dotenv import load_dotenv
load_dotenv("/opt/st_faktura/.env")

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import api


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    number = int(sys.argv[1])

    local_path = api._invoice_pdf_path(number)
    if not local_path:
        print(f"No local PDF for invoice {number}")
        return 1
    with open(local_path, "rb") as fh:
        local_bytes = fh.read()
    print(f"local : {local_path}  {len(local_bytes)} bytes  md5 {md5(local_bytes)}")

    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
    if not folder_id:
        print("GOOGLE_DRIVE_FOLDER_ID not set")
        return 1
    keyfile = (
        os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or os.getenv("SERVICE_ACCOUNT_FILE")
        or "service_account.json"
    )
    creds = service_account.Credentials.from_service_account_file(
        keyfile, scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    name = os.path.basename(local_path)
    found = drive.files().list(
        q=f"'{folder_id}' in parents and name='{name}' and trashed=false",
        fields="files(id,name,size,modifiedTime,md5Checksum)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute().get("files", [])
    print(f"drive : {len(found)} file(s) named {name} in folder {folder_id}")
    for item in found:
        print("        ", item.get("id"), item.get("size"), "bytes", item.get("modifiedTime"),
              "md5", item.get("md5Checksum"))

    media = MediaFileUpload(local_path, mimetype="application/pdf", resumable=False)
    if found:
        target = found[0]
        updated = drive.files().update(
            fileId=target["id"],
            media_body=media,
            fields="id,name,size,modifiedTime,md5Checksum",
            supportsAllDrives=True,
        ).execute()
        print("replaced existing fileId:", updated.get("id"))
    else:
        updated = drive.files().create(
            body={"name": name, "parents": [folder_id]},
            media_body=media,
            fields="id,name,size,modifiedTime,md5Checksum",
            supportsAllDrives=True,
        ).execute()
        print("uploaded new fileId (no existing copy):", updated.get("id"))
    print("drive now:", updated.get("name"), updated.get("size"), "bytes",
          updated.get("modifiedTime"), "md5", updated.get("md5Checksum"))

    # Verify by downloading what Drive actually holds.
    content = drive.files().get_media(fileId=updated["id"], supportsAllDrives=True).execute()
    remote_md5 = md5(content)
    print(f"verified: downloaded {len(content)} bytes  md5 {remote_md5}")
    ok = remote_md5 == md5(local_bytes)
    print("MATCH" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
