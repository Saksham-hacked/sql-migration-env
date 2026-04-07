# server/app.py — re-exports main app; satisfies multi-mode deployment validator
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from main import app  # noqa: F401


def main():
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=False)


if __name__ == "__main__":
    main()
