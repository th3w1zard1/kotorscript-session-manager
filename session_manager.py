#!/usr/bin/env python3
import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/", response_class=HTMLResponse)
async def index():
    template_path = Path("/tmp/templates/index.html")
    if template_path.exists():
        return template_path.read_text()
    return "<html><body><h1>Session Manager</h1><p>Service is running</p></body></html>"

@app.get("/waiting", response_class=HTMLResponse)
async def waiting():
    template_path = Path("/tmp/templates/waiting.html")
    if template_path.exists():
        return template_path.read_text()
    return "<html><body><h1>Waiting</h1></body></html>"

if __name__ == "__main__":
    port = int(os.getenv("SESSION_MANAGER_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
