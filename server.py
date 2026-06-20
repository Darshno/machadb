"""
server.py — MachaDB Web API & Frontend Server

This is the bridge between the beautiful chaos of our database
and the clean, sterile world of HTTP REST APIs.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import traceback
import os

from machadb import MachaDB
from machadb.errors import MachaError

# Configuration
DATA_DIR = os.environ.get("MACHADB_DATA_DIR", "./machadb_data")

# The Database Instance
print(f"Booting MachaDB from {DATA_DIR}...")
db = MachaDB(DATA_DIR)

# The Web App
app = FastAPI(title="MachaDB API", version="1.0.0-chai-powered")

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    success: bool
    data: list | str | dict | None = None
    error: str | None = None

# API Endpoints
@app.post("/api/query", response_model=QueryResponse)
def execute_query(req: QueryRequest):
    """Execute a raw MachaDB query and return the results."""
    if not req.query.strip():
        return QueryResponse(success=False, error="Khali query kottidya macha?")
        
    try:
        result = db.execute(req.query)
        return QueryResponse(success=True, data=result)
    except MachaError as e:
        # Our custom slang errors
        return QueryResponse(success=False, error=str(e))
    except Exception as e:
        # Something crashed internally
        traceback.print_exc()
        return QueryResponse(success=False, error=f"ayyo macha, Python crash aagide! {str(e)}")

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_ui():
    """Serve the Web UI playground."""
    return FileResponse("static/index.html")

# Cleanup hook
@app.on_event("shutdown")
def shutdown_event():
    print("Flushing and closing Godaamu...")
    db.close()
    print("Bye macha!")
