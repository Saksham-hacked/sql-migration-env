# app.py — root entrypoint required by Hugging Face Spaces.
# Re-exports `app` from main.py so HF's validator finds it.
# The Dockerfile still runs: uvicorn main:app --host 0.0.0.0 --port 7860

from main import app  # noqa: F401
