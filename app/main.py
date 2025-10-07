from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os, pandas as pd
from .run_script import run_repo_script, REPO_DIR, PLOTS_DIR

app = FastAPI(title="Trade Wrapper", version="0.1.0")

# Serve generated plots as static files (if the repo has a plots dir)
if os.path.isdir(PLOTS_DIR):
    app.mount("/plots", StaticFiles(directory=PLOTS_DIR), name="plots")

@app.get("/")
def index():
    return HTMLResponse(
        "<h1>Trade</h1>"
        "<p>Simple wrapper UI.</p>"
        "<ul>"
        "<li><a href='/api/run/plot?symbol=AAPL&days=30'>Run plot.py (AAPL 30d)</a></li>"
        "<li><a href='/api/view/csv?file=example.csv'>View CSV (example)</a></li>"
        "</ul>"
    )

@app.get("/api/run/plot")
def run_plot(symbol: str = Query("AAPL"), days: int = Query(30)):
    # Adjust to your friend’s real CLI args if needed
    res = run_repo_script("plot.py", [symbol, str(days)])
    if res["returncode"] != 0:
        raise HTTPException(500, f"plot.py failed:\n{res['stderr']}")
    urls = [f"/plots/{os.path.basename(p)}" for p in res["plots"]]
    return JSONResponse({"ok": True, "plots": urls, "stdout": res["stdout"]})

@app.get("/api/view/csv")
def view_csv(file: str):
    path = os.path.join(REPO_DIR, file)
    if not (path.endswith(".csv") and os.path.isfile(path)):
        raise HTTPException(404, "CSV not found")
    df = pd.read_csv(path)
    return HTMLResponse(df.to_html(index=False))
