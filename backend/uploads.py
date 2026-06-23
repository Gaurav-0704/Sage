"""
Tiny file-storage helper for assignment submissions.

Files are written under backend/uploads/ with a uuid prefix so names never
collide. The directory is gitignored. On an ephemeral host (e.g. Railway
without a volume) uploads do not survive a redeploy — fine for an MVP; attach
a volume or object storage for production durability.
"""

import os
import uuid
from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
MAX_BYTES = 10 * 1024 * 1024   # 10 MB


def _ensure_dir():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_bytes(original_name: str, data: bytes) -> tuple[str, str]:
    """Persist bytes; return (display_name, stored_path). Raises ValueError if too big."""
    if len(data) > MAX_BYTES:
        raise ValueError("File too large (max 10 MB).")
    _ensure_dir()
    safe = os.path.basename(original_name or "upload")
    stored = UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe}"
    with open(stored, "wb") as f:
        f.write(data)
    return safe, str(stored)
