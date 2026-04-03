# app.py — required by Hugging Face Spaces as the entrypoint marker.
# The actual application is defined in main.py; we just re-export `app` here
# so that both `uvicorn app:app` and `uvicorn main:app` work identically.

from main import app  # noqa: F401  re-export for HF Spaces discovery
