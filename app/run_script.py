import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Iterable, Sequence


def _default_repo_dir() -> Path:
    env_dir = os.getenv("REPO_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    # Local development fallback – the trade repo lives beside this wrapper.
    return Path(__file__).resolve().parents[1] / "trade-repo"


REPO_DIR = _default_repo_dir()
PLOTS_DIR = (REPO_DIR / "plots").resolve()


def _load_allowed_scripts() -> set[str]:
    env = os.getenv("ALLOWED_SCRIPTS")
    if not env:
        return {"plot.py", "csvViewer.py", "returns.py", "options.py"}
    names: Iterable[str] = (part.strip() for part in env.split(","))
    return {Path(name).name for name in names if name}


ALLOWED_SCRIPTS = _load_allowed_scripts()


def _ensure_plots_dir() -> None:
    try:
        PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise RuntimeError(f"Unable to create plots directory at {PLOTS_DIR}") from exc


def _snapshot_plot_dir() -> dict[str, int]:
    if not PLOTS_DIR.is_dir():
        return {}
    return {
        item.name: int(item.stat().st_mtime_ns)
        for item in PLOTS_DIR.iterdir()
        if item.is_file()
    }


def _collect_new_plots(before: dict[str, int]) -> list[Path]:
    if not PLOTS_DIR.is_dir():
        return []
    updated: list[Path] = []
    for path in PLOTS_DIR.iterdir():
        if not path.is_file():
            continue
        previous = before.get(path.name)
        current = int(path.stat().st_mtime_ns)
        if previous is None or current > previous:
            updated.append(path)
    return sorted(updated, key=lambda item: item.stat().st_mtime_ns)


def _session_plot_dir(session_id: str) -> Path:
    return PLOTS_DIR / f"session-{session_id}"


def run_repo_script(
    script: str,
    args: Sequence[str] | None = None,
    timeout: int = 120,
) -> dict[str, object]:
    """Execute an allowed script from the cloned trading repo.

    The command is executed inside the trading repository so that relative file
    access continues to work.  Newly created or modified plot files are copied
    into a session specific directory in ``plots`` so that concurrent users do
    not clobber each other's files.
    """

    args = list(args or [])
    if script not in ALLOWED_SCRIPTS:
        raise ValueError(f"Forbidden script: {script!r}")

    if "/" in script or script.startswith(".."):
        raise ValueError("Script name may not contain path separators")

    script_path = REPO_DIR / script
    if not script_path.is_file():
        raise FileNotFoundError(f"Script not found: {script_path}")

    _ensure_plots_dir()
    before_snapshot = _snapshot_plot_dir()

    session_id = uuid.uuid4().hex[:12]
    session_dir = _session_plot_dir(session_id)
    workdir = Path(tempfile.mkdtemp(prefix="sess-", dir="/tmp"))

    cmd = ["python", str(script_path), *map(str, args)]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    new_plots: list[str] = []
    if proc.returncode == 0:
        for plot in _collect_new_plots(before_snapshot):
            session_dir.mkdir(parents=True, exist_ok=True)
            dest = session_dir / plot.name
            try:
                shutil.copy2(plot, dest)
            except FileNotFoundError:
                # Plot disappeared between listing and copy; skip it.
                continue
            new_plots.append(f"/plots/{session_dir.name}/{dest.name}")
    else:
        # Ensure failed runs do not leak empty session directories.
        if session_dir.exists() and not any(session_dir.iterdir()):
            session_dir.rmdir()

    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-10000:],
        "stderr": proc.stderr[-10000:],
        "plots": new_plots,
        "workdir": str(workdir),
        "session": session_dir.name if session_dir.exists() else None,
    }
