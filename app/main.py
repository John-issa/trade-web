# app/main.py
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from .shim_runner import run_script_headless

REPO = Path(os.environ.get("REPO_DIR", "/srv/trade-repo"))
OUT  = Path(os.environ.get("OUTPUT_DIR", "/data/captures"))

app = FastAPI()
app.mount("/captures", StaticFiles(directory=OUT, html=True), name="captures")

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <h1>trade-web</h1>
    <p>Examples:</p>
    <ul>
      <li><a href="/run/csvViewer.py">Run csvViewer.py</a></li>
    </ul>
    <p>Outputs appear under <a href="/captures/" target="_blank">/captures/</a></p>
    """

@app.get("/run/{script_name}", response_class=HTMLResponse)
def run_script(script_name: str):
    script_path = REPO / script_name
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Script not found")
    result = run_script_headless(script_path, OUT)
    links = "".join(f"<li><a href='/captures/{n}' target='_blank'>{n}</a></li>" for n in result["outputs"])
    printed = f"<pre>{result['printed']}</pre>" if result["printed"] else "<em>(no output)</em>"
    return f"<h2>Ran: {script_name}</h2><h3>Captured Files</h3><ul>{links or '<li>(none)</li>'}</ul><h3>Logs</h3>{printed}"
