from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .run_script import ALLOWED_SCRIPTS, PLOTS_DIR, REPO_DIR, run_repo_script


app = FastAPI(title="Trade Wrapper", version="0.1.0")

# Serve generated plots as static files (if the repo has a plots dir)
if PLOTS_DIR.exists():
    app.mount("/plots", StaticFiles(directory=str(PLOTS_DIR)), name="plots")


def _list_available_csvs() -> list[str]:
    search_roots: Iterable[Path] = [REPO_DIR]
    csvs: list[str] = []
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.csv"):
            try:
                rel = path.relative_to(REPO_DIR)
            except ValueError:
                continue
            csvs.append(rel.as_posix())
    return sorted(csvs)[:50]


@app.get("/")
def index():
    script_links = "".join(
        f"<li><a href='/api/run/plot?symbol=AAPL&days=30'>plot.py (example)</a></li>"
        if script == "plot.py"
        else f"<li><a href='/api/run/script?name={script}'>Run {script}</a></li>"
        for script in sorted(ALLOWED_SCRIPTS)
    )
    csv_links = "".join(
        f"<li><a href='/api/view/csv?file={path}'>{path}</a></li>"
        for path in _list_available_csvs()
    )
    html = [
        "<h1>Trade</h1>",
        "<p>Simple wrapper UI.</p>",
        "<h2>Scripts</h2>",
        f"<ul>{script_links or '<li>No scripts configured.</li>'}</ul>",
    ]
    if csv_links:
        html.extend(["<h2>CSV files</h2>", f"<ul>{csv_links}</ul>"])
    return HTMLResponse("".join(html))


@app.get("/api/run/plot")
def run_plot(symbol: str = Query("AAPL"), days: int = Query(30)):
    # Adjust to your friend’s real CLI args if needed
    res = run_repo_script("plot.py", [symbol, str(days)])
    if res["returncode"] != 0:
        raise HTTPException(500, f"plot.py failed:\n{res['stderr']}")
    return JSONResponse({"ok": True, "plots": res["plots"], "stdout": res["stdout"]})


@app.get("/api/run/script")
def run_script(name: str = Query(..., description="Script filename, e.g. plot.py")):
    res = run_repo_script(name)
    if res["returncode"] != 0:
        raise HTTPException(500, f"{name} failed:\n{res['stderr']}")
    return JSONResponse({"ok": True, "plots": res["plots"], "stdout": res["stdout"]})


@app.get("/api/view/csv")
def view_csv(file: str):
    requested = (REPO_DIR / file).resolve()
    if not requested.is_file() or requested.suffix.lower() != ".csv":
        raise HTTPException(404, "CSV not found")
    try:
        requested.relative_to(REPO_DIR)
    except ValueError:
        raise HTTPException(403, "CSV outside repository scope")

    df = pd.read_csv(requested)
    return HTMLResponse(df.to_html(index=False))
