# app/main.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .run_script import ALLOWED_SCRIPTS, REPO_DIR, PLOTS_DIR, run_repo_script


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>trade-web</title>
  <style>
    :root {
      color-scheme: dark;
      font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    body {
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(circle at top, #1f2937, #0f172a 65%);
      color: #e2e8f0;
      display: flex;
      justify-content: center;
    }
    main {
      width: min(100%, 1080px);
      padding: 3rem clamp(1rem, 5vw, 4rem);
      box-sizing: border-box;
    }
    h1 {
      font-size: clamp(2rem, 4vw, 3rem);
      margin-bottom: 0.5rem;
    }
    p.lead {
      color: #cbd5f5;
      margin-top: 0;
      margin-bottom: 2.5rem;
    }
    section {
      margin-bottom: 3rem;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(148, 163, 184, 0.2);
      border-radius: 18px;
      padding: 1.5rem;
      box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.45);
      backdrop-filter: blur(8px);
    }
    section h2 {
      font-size: 1.25rem;
      margin-top: 0;
      margin-bottom: 1rem;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      color: #a5b4fc;
    }
    #scripts {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
    }
    #scripts button {
      appearance: none;
      border: 1px solid transparent;
      border-radius: 999px;
      padding: 0.65rem 1.4rem;
      font-size: 0.95rem;
      letter-spacing: 0.02em;
      font-weight: 600;
      cursor: pointer;
      transition: transform 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
      color: #0f172a;
      background: linear-gradient(120deg, #facc15, #f97316);
      box-shadow: 0 12px 30px -10px rgba(249, 115, 22, 0.5);
    }
    #scripts button:hover {
      transform: translateY(-1px);
      box-shadow: 0 16px 35px -12px rgba(249, 115, 22, 0.6);
    }
    #scripts button:disabled {
      cursor: wait;
      opacity: 0.65;
      transform: none;
      box-shadow: none;
    }
    #scripts button.active {
      border-color: rgba(15, 23, 42, 0.45);
      box-shadow: 0 18px 35px -12px rgba(59, 130, 246, 0.55);
      background: linear-gradient(120deg, #60a5fa, #818cf8);
    }
    .empty-state {
      color: #94a3b8;
      font-style: italic;
    }
    #status {
      font-weight: 600;
      font-size: 1.05rem;
      margin: 0 0 1rem;
    }
    #status.success { color: #4ade80; }
    #status.error { color: #f87171; }
    .result.hidden { display: none; }
    details {
      margin-top: 1rem;
      border: 1px solid rgba(148, 163, 184, 0.15);
      border-radius: 12px;
      background: rgba(30, 41, 59, 0.6);
      padding: 0.75rem 1rem;
    }
    summary {
      cursor: pointer;
      font-weight: 600;
      color: #e2e8f0;
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0.75rem 0 0;
      font-family: 'Source Code Pro', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
      background: rgba(15, 23, 42, 0.65);
      border-radius: 12px;
      padding: 1rem;
      font-size: 0.85rem;
      line-height: 1.55;
      color: #e5e7eb;
    }
    .plots {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1rem;
      margin-top: 1.5rem;
    }
    figure {
      margin: 0;
      background: rgba(15, 23, 42, 0.65);
      border-radius: 18px;
      overflow: hidden;
      border: 1px solid rgba(148, 163, 184, 0.1);
      box-shadow: 0 18px 32px -18px rgba(15, 23, 42, 0.75);
    }
    figure img {
      display: block;
      width: 100%;
      height: auto;
    }
    figure figcaption {
      padding: 0.75rem 1rem;
      font-size: 0.85rem;
      color: #cbd5f5;
    }
    footer {
      text-align: center;
      color: #64748b;
      font-size: 0.85rem;
      margin-top: 3rem;
    }
    @media (max-width: 640px) {
      section { padding: 1rem; }
      #scripts { flex-direction: column; }
      #scripts button { width: 100%; justify-content: center; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>trade-web</h1>
      <p class="lead">Run trading assistant scripts directly in your browser — no popups required.</p>
    </header>

    <section>
      <h2>Available scripts</h2>
      <div id="scripts" aria-live="polite">
        <span class="empty-state">Loading scripts…</span>
      </div>
    </section>

    <section id="result" class="result hidden">
      <h2>Execution details</h2>
      <p id="status"></p>
      <div id="session-info" class="session"></div>
      <div id="plots" class="plots"></div>
      <details open>
        <summary>Standard output</summary>
        <pre id="stdout"></pre>
      </details>
      <details id="stderr-block">
        <summary>Standard error</summary>
        <pre id="stderr"></pre>
      </details>
    </section>

    <footer>
      Powered by FastAPI · Sessions are isolated per run so multiple users can work in parallel.
    </footer>
  </main>

  <script>
    const scriptsContainer = document.getElementById('scripts');
    const resultSection = document.getElementById('result');
    const statusText = document.getElementById('status');
    const stdoutPre = document.getElementById('stdout');
    const stderrPre = document.getElementById('stderr');
    const stderrBlock = document.getElementById('stderr-block');
    const plotsContainer = document.getElementById('plots');
    const sessionInfo = document.getElementById('session-info');

    function setButtonsDisabled(disabled) {
      const buttons = scriptsContainer.querySelectorAll('button');
      buttons.forEach(button => {
        button.disabled = disabled;
      });
    }

    function setActiveButton(name) {
      const buttons = scriptsContainer.querySelectorAll('button');
      buttons.forEach(button => {
        button.classList.toggle('active', button.dataset.script === name);
      });
    }

    function renderPlots(plots) {
      plotsContainer.innerHTML = '';
      if (!plots || plots.length === 0) {
        return;
      }
      plots.forEach(url => {
        const figure = document.createElement('figure');
        const img = document.createElement('img');
        img.src = url;
        img.alt = 'Generated output';
        const caption = document.createElement('figcaption');
        caption.textContent = url.split('/').pop();
        figure.appendChild(img);
        figure.appendChild(caption);
        plotsContainer.appendChild(figure);
      });
    }

    async function runScript(name) {
      setButtonsDisabled(true);
      setActiveButton(name);
      resultSection.classList.remove('hidden');
      statusText.className = '';
      statusText.textContent = `Running ${name}…`;
      sessionInfo.textContent = '';
      stdoutPre.textContent = '';
      stderrPre.textContent = '';
      stderrBlock.open = false;
      plotsContainer.innerHTML = '';

      try {
        const response = await fetch('/api/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ script: name }),
        });

        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.detail || `Failed to execute ${name}`);
        }

        const data = await response.json();
        const ok = data.returncode === 0;
        statusText.textContent = ok ? `Finished ${name} successfully` : `Script exited with code ${data.returncode}`;
        statusText.className = ok ? 'success' : 'error';
        stdoutPre.textContent = data.stdout || '(no stdout)';
        stderrPre.textContent = data.stderr || '(no stderr)';
        stderrBlock.style.display = data.stderr ? 'block' : 'none';
        if (data.session) {
          sessionInfo.textContent = `Session: ${data.session}`;
        } else {
          sessionInfo.textContent = '';
        }
        renderPlots(Array.isArray(data.plots) ? data.plots : []);
      } catch (error) {
        statusText.textContent = error.message;
        statusText.className = 'error';
        stderrBlock.style.display = 'none';
      } finally {
        setButtonsDisabled(false);
      }
    }

    async function loadScripts() {
      try {
        const response = await fetch('/api/scripts');
        if (!response.ok) {
          throw new Error('Unable to fetch scripts');
        }
        const data = await response.json();
        const scripts = Array.isArray(data.scripts) ? data.scripts : [];
        if (scripts.length === 0) {
          scriptsContainer.innerHTML = '<span class="empty-state">No scripts available. Verify the repository mount and ALLOWED_SCRIPTS.</span>';
          return;
        }

        scriptsContainer.innerHTML = '';
        scripts.forEach(name => {
          const button = document.createElement('button');
          button.textContent = name;
          button.dataset.script = name;
          button.addEventListener('click', () => runScript(name));
          scriptsContainer.appendChild(button);
        });
      } catch (error) {
        scriptsContainer.innerHTML = `<span class="empty-state">${error.message}</span>`;
      }
    }

    loadScripts();
  </script>
  </body>
</html>
"""


app = FastAPI(title="trade-web")


def _resolve_allowed_scripts() -> list[str]:
    names: Iterable[str] = sorted(ALLOWED_SCRIPTS)
    resolved: list[str] = []
    for candidate in names:
        candidate_name = Path(candidate).name
        if not candidate_name:
            continue
        script_path = REPO_DIR / candidate_name
        if script_path.is_file():
            resolved.append(candidate_name)
    return resolved


app.mount(
    "/plots",
    StaticFiles(directory=str(PLOTS_DIR), html=False, check_dir=False),
    name="plots",
)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(content=HTML_PAGE)


class RunRequest(BaseModel):
    script: str
    args: list[str] | None = None


@app.get("/api/scripts")
def list_scripts() -> dict[str, list[str]]:
    return {"scripts": _resolve_allowed_scripts()}


@app.post("/api/run")
def run_script(payload: RunRequest) -> dict[str, object]:
    script_name = Path(payload.script).name
    if script_name not in _resolve_allowed_scripts():
        raise HTTPException(status_code=400, detail="Script is not allowed or missing")

    try:
        result = run_repo_script(script_name, payload.args or [])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"script": script_name, **result}
