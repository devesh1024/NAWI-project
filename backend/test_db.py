# Allow running this file directly from anywhere (`python backend/test_db.py` from the
# repo root, or `python test_db.py` from backend/) as well as `python -m backend.test_db`.
# The app imports as `backend.app...`, so the repo root must be on sys.path.
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.app.database.connection import engine

try:
    with engine.connect() as connection:
        print("✅ Database connected successfully!")
except Exception as e:
    print("❌ Database connection failed:")
    print(e)
