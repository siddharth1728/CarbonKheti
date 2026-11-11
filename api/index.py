"""Vercel Python serverless entrypoint exposing the FastAPI app."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app, ensure_initialized  # noqa: E402,F401

ensure_initialized()
