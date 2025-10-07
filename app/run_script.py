import os, subprocess, tempfile, pathlib, shlex, uuid

REPO_DIR = os.getenv("REPO_DIR", "/app/trade")
PLOTS_DIR = os.path.join(REPO_DIR, "plots")
ALLOWED_SCRIPTS = {"plot.py","csvViewer.py","returns.py","options.py"}

def run_repo_script(script: str, args: list[str], timeout: int = 120):
    if script not in ALLOWED_SCRIPTS:
        raise ValueError("Forbidden script")

    # Isolate each run a bit
    workdir = tempfile.mkdtemp(prefix="sess-", dir="/tmp")
    cmd = ["python", os.path.join(REPO_DIR, script), *args]
    proc = subprocess.run(
        cmd, cwd=REPO_DIR, capture_output=True, text=True, timeout=timeout
    )
    plots = []
    if os.path.isdir(PLOTS_DIR):
        plots = [str(p) for p in pathlib.Path(PLOTS_DIR).iterdir() if p.is_file()]
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-10000:],
        "stderr": proc.stderr[-10000:],
        "plots": plots,
        "workdir": workdir,
    }
