# app/shim_runner.py
import os, io, time, runpy, sys
from pathlib import Path

def run_script_headless(script_path: Path, outdir: Path) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)

    # Headless matplotlib everywhere
    os.environ.setdefault("MPLBACKEND", "Agg")

    # Capture stdout/stderr
    stdio = io.StringIO()
    orig_stdout, orig_stderr = sys.stdout, sys.stderr

    # Patch plt.show() -> save figures
    import builtins
    _orig_import = builtins.__import__

    def _save_all_figs(tag="figure"):
        try:
            import matplotlib.pyplot as plt
            for i in plt.get_fignums():
                fig = plt.figure(i)
                ts = time.strftime("%Y%m%d-%H%M%S")
                fig.savefig(outdir / f"{tag}-{i}-{ts}.png", bbox_inches="tight")
            try: plt.close('all')
            except Exception: pass
        except Exception:
            pass

    def _patched_import(name, *a, **k):
        mod = _orig_import(name, *a, **k)
        if name == "matplotlib.pyplot":
            try:
                import matplotlib.pyplot as plt
                def _save_instead(*_a, **_k): _save_all_figs()
                plt.show = _save_instead
            except Exception:
                pass
        return mod

    builtins.__import__ = _patched_import

    # Run the script from its own folder
    cwd0 = os.getcwd()
    try:
        os.chdir(script_path.parent)
        if str(script_path.parent) not in sys.path:
            sys.path.insert(0, str(script_path.parent))
        sys.stdout = sys.stderr = stdio
        runpy.run_path(str(script_path), run_name="__main__")
    finally:
        sys.stdout, sys.stderr = orig_stdout, orig_stderr
        builtins.__import__ = _orig_import
        os.chdir(cwd0)
        _save_all_figs(tag="autosaved")

    printed = stdio.getvalue()
    outputs = sorted(p.name for p in outdir.iterdir() if p.is_file())
    return {"outputs": outputs, "printed": printed}
