#!/bin/bash
echo "Starting Cafe24 Automation Hub (Development Mode)"
echo "Server will be available at: http://localhost:3000"
echo
cd "$(dirname "$0")"
python -m uvicorn web.app:app --reload --port 3000