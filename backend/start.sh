#!/bin/bash
cd /home/fujel/Documents/Fujel-Developer/Voice\ Assistent\ vs\ code/jarvis/backend
source .venv/bin/activate
exec python -m uvicorn api.fastapi_app:app --host 127.0.0.1 --port 8765