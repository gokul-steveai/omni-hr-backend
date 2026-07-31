# OmniHR Backend API

FastAPI backend application for OmniHR Enterprise System. Managed with `uv`.

## Quickstart

```bash
# Sync dependencies
uv sync

# Run database seed
uv run python scripts/seed_db.py

# Run FastAPI server
uv run uvicorn app.main:app --reload --port 8000
```
