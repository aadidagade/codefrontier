#!/usr/bin/env bash
echo "==> Running database migrations..."
python -m alembic upgrade head || echo "==> Notice: Database migration skipped or database not yet connected. Continuing startup..."

echo "==> Starting FastAPI Uvicorn server on port ${PORT:-8000}..."
cd backend
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
