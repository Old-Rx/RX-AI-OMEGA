#!/bin/sh
set -eu
alembic upgrade head
exec uvicorn rx_ai_omega.main:app --host 0.0.0.0 --port 8000 --proxy-headers
