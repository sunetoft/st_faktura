from __future__ import annotations

import json
import os
import shutil
import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def _data_dir() -> Path:
    d = Path(os.getenv("DATA_DIR", "/opt/st_faktura/data"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _resolve(blob_name: str) -> Path:
    path = _data_dir() / blob_name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_json_from_gcs(
    bucket_name: str, blob_name: str, default: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    path = _resolve(blob_name)
    if not path.exists():
        return default or {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Return any valid JSON (dict or list), not just dict
        if isinstance(data, (dict, list)):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return default or {}


def write_json_to_gcs(bucket_name: str, blob_name: str, data: Dict[str, Any]) -> None:
    path = _resolve(blob_name)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def upload_file_to_gcs(
    bucket_name: str, blob_name: str, file_path: str, content_type: Optional[str] = None
) -> str:
    dest = _resolve(blob_name)
    shutil.copy2(file_path, dest)
    return f"local://{dest}"


def download_blob_to_path(bucket_name: str, blob_name: str, dest_path: str) -> None:
    shutil.copy2(_resolve(blob_name), dest_path)


class _LocalBlob:
    def __init__(self, path: Path, relative: str) -> None:
        self.name = relative
        self._path = path
        self.updated: Optional[datetime.datetime] = datetime.datetime.fromtimestamp(
            path.stat().st_mtime
        )

    def download_as_text(self, encoding: str = "utf-8") -> str:
        return self._path.read_text(encoding=encoding)


def list_blobs(bucket_name: str, prefix: str) -> Iterable[str]:
    base = _data_dir() / prefix
    if not base.exists():
        return
    for p in sorted(base.rglob("*")):
        if p.is_file():
            yield str(p.relative_to(_data_dir()))


def list_blob_objects(bucket_name: str, prefix: str) -> Iterable[_LocalBlob]:
    base = _data_dir() / prefix
    if not base.exists():
        return
    for p in sorted(base.rglob("*")):
        if p.is_file():
            yield _LocalBlob(p, str(p.relative_to(_data_dir())))


def get_env_bucket() -> str:
    # No real bucket — return a placeholder so callers that check this value work fine.
    return "local"


def get_env_prefix() -> str:
    return os.getenv("GCS_PREFIX", "st-faktura").strip().strip("/")
