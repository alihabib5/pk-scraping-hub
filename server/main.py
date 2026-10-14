"""
PK-Hub Server Entrypoint
Allows running directly:
  uvicorn main:app --reload --port 8000
  uvicorn app.main:app --reload --port 8000
  python main.py
"""
from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

