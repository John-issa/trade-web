from __future__ import annotations

from subprocess import TimeoutExpired

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .run_script import PLOTS_DIR, REPO_DIR, run_repo_script


app = FastAPI(title="Trade Wrapper", version="0.1.0")

# Serve generated plots as static files (if the repo has a plots dir)
if PLOTS_DIR.exists():
    app.mount("/plots", StaticFiles(directory=str(PLOTS_DIR)), name="plots")


def _render_csv_viewer_page(result: dict[str, object]) -> HTMLResponse:
    """Turn the output of ``csvViewer.py`` into an embeddable HTML page."""

    stdout = str(result.get("stdout") or "").strip()
    plots = [path for path in result.get("plots", []) if isinstance(path, str)]

    body: list[str] = [
        "<style>body{font-family:system-ui, sans-serif;margin:0;background:#111;color:#f5f5f5;}",
        "main{display:flex;flex-direction:column;height:100vh;}",
        "header{padding:1.5rem 2rem;border-bottom:1px solid #333;}",
        "header h1{margin:0;font-size:1.5rem;}",
        "section.viewer{flex:1;min-height:0;padding:1rem 2rem;overflow:auto;background:#1b1b1b;}",
        "iframe{border:0;width:100%;height:100%;background:#fff;border-radius:0.5rem;}",
        "pre{background:#000;padding:1rem;border-radius:0.5rem;overflow:auto;}</style>",
        "<main>",
        "<header><h1>csvViewer.py</h1><p>Latest output from the trading assistant.</p></header>",
        "<section class='viewer'>",
    ]

    iframe_src = next((plot for plot in reversed(plots) if plot.endswith(".html")), None)
    if iframe_src:
        body.append(f"<iframe src='{iframe_src}' title='csvViewer output'></iframe>")
    elif stdout:
        escaped = stdout.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        body.append(f"<pre>{escaped}</pre>")
    else:
        body.append(
            "<pre>No output captured from csvViewer.py. Check the script for details.</pre>"
        )

    body.extend(["</section>", "</main>"])
    return HTMLResponse("".join(body))


@app.get("/")
def index():
    try:
        result = run_repo_script("csvViewer.py")
    except FileNotFoundError as exc:
        raise HTTPException(500, f"csvViewer.py is not available: {exc}") from exc
    except TimeoutExpired as exc:
        raise HTTPException(504, f"csvViewer.py timed out: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc

    if result.get("returncode") != 0:
        stderr = str(result.get("stderr") or "").strip()
        raise HTTPException(500, f"csvViewer.py failed:\n{stderr}")

    return _render_csv_viewer_page(result)


@app.get("/api/run/plot")
def run_plot(symbol: str = Query("AAPL"), days: int = Query(30)):
    # Adjust to your friend’s real CLI args if needed
    try:
        res = run_repo_script("plot.py", [symbol, str(days)])
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except TimeoutExpired as exc:
        raise HTTPException(504, f"plot.py timed out: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
    if res["returncode"] != 0:
        raise HTTPException(500, f"plot.py failed:\n{res['stderr']}")
    return JSONResponse({"ok": True, "plots": res["plots"], "stdout": res["stdout"]})


@app.get("/api/run/script")
def run_script(name: str = Query(..., description="Script filename, e.g. plot.py")):
    try:
        res = run_repo_script(name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except TimeoutExpired as exc:
        raise HTTPException(504, f"{name} timed out: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
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
