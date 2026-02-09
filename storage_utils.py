"""
GCS storage helpers for Cloud Run deployments.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Optional

from google.cloud import storage


def get_gcs_client() -> storage.Client:
    return storage.Client()


def read_json_from_gcs(bucket_name: str, blob_name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    if not blob.exists():
        return default or {}
    data = blob.download_as_text(encoding="utf-8")
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        return default or {}
    if isinstance(parsed, dict):
        return parsed
    return default or {}


def write_json_to_gcs(bucket_name: str, blob_name: str, data: Dict[str, Any]) -> None:
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    blob.upload_from_string(payload, content_type="application/json")


def upload_file_to_gcs(bucket_name: str, blob_name: str, file_path: str, content_type: Optional[str] = None) -> str:
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path, content_type=content_type)
    return f"gs://{bucket_name}/{blob_name}"


def download_blob_to_path(bucket_name: str, blob_name: str, dest_path: str) -> None:
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(dest_path)


def list_blobs(bucket_name: str, prefix: str) -> Iterable[str]:
    client = get_gcs_client()
    for blob in client.list_blobs(bucket_name, prefix=prefix):
        yield blob.name


def list_blob_objects(bucket_name: str, prefix: str) -> Iterable[storage.Blob]:
    client = get_gcs_client()
    for blob in client.list_blobs(bucket_name, prefix=prefix):
        yield blob


def get_env_bucket() -> str:
    bucket = os.getenv("GCS_BUCKET", "").strip()
    if not bucket:
        raise ValueError("GCS_BUCKET is not configured")
    return bucket


def get_env_prefix() -> str:
    prefix = os.getenv("GCS_PREFIX", "st-faktura").strip().strip("/")
    return prefix
