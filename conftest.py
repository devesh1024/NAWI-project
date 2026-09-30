# Root conftest: puts the repo root on sys.path (so `backend.app...` imports
# resolve no matter where pytest is launched) and keeps pytest away from files
# that are scripts or route modules, not tests.
collect_ignore = ["backend/test_db.py"]
collect_ignore_glob = ["backend/app/*"]
