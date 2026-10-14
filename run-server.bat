@echo off
echo Starting PK-Hub FastAPI Backend...
cd /d "%~dp0server"

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -r requirements.txt

set PYTHONPATH=%cd%
uvicorn app.main:app --reload --port 8000
