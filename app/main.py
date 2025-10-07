# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .shim_runner import run_script_headless

import os
from pathlib import Path

ROOT = Path("/app")
REPO = Path(os.environ.get("REPO_DIR", "/srv/trade-repo"))
OUT  = Path(os.environ.get("OUTPUT_DIR", "/data/captures"))

app = FastAPI()
app.mount("/captures", StaticFiles(directory=OUT, html=True), name="captures")

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <h1>trade-web</h1>
    <p>Try running a script:</p>
    <ul>
      <li><a href="/run/csvViewer.py">csvViewer.py</a></li>
      <li><a href="/run/some_other_script.py">some_other_script.py</a></li>
    </ul>
    """

@app.get("/run/{script_name}", response_class=HTMLResponse)
def run_script(script_name: str):
    script_path = REPO / script_name
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Script not found")
    result = run_script_headless(script_path, OUT)
    links = "".join(f"<li><a href='/captures/{name}' target='_blank'>{name}</a></li>"
                    for name in result["outputs"])
    opened = "".join(f"<li>{x}</li>" for x in result["opened"])
    printed = f"<pre>{result['printed']}</pre>" if result["printed"] else ""
    return f"""
      <h2>Ran: {script_name}</h2>
      <h3>Captured Files</h3><ul>{links or "<li>(none)</li>"}</ul>
      <h3>Intercepted webbrowser.open()</h3><ul>{opened or "<li>(none)</li>"}</ul>
      <h3>Stdout/Stderr</h3>{printed}
    """
