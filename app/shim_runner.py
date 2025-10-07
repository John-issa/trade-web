# app/shim_runner.py
import os, io, time, runpy, webbrowser
from pathlib import Path

def run_script_headless(script_path: Path, outdir: Path) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)

    # 1) Headless matplotlib
    os.environ.setdefault("MPLBACKEND", "Agg")
    # Make sure trade-repo code sees where to drop outputs if it respects PLOTS_DIR
    os.environ.setdefault("PLOTS_DIR", str(outdir))

    # 2) Capture webbrowser.open(...)
    opened_targets = []
    real_open = webbrowser.open

    def _capture_open(url, *_a, **_k):
        opened_targets.append(url)
        # Pretend success; we don't actually open a system browser
        return True

    webbrowser.open = _capture_open

    # 3) Capture plt.show() by saving all live figures
    # We import lazily so we don't crash if matplotlib isn't used.
    def save_all_figs(tag="figure"):
        try:
            import matplotlib.pyplot as plt
            for i in plt.get_fignums():
                fig = plt.figure(i)
                ts = time.strftime("%Y%m%d-%H%M%S")
                out = outdir / f"{tag}-{i}-{ts}.png"
                fig.savefig(out, bbox_inches="tight")
            plt.close('all')
        except Exception:
            pass

    # Monkey-patch plt.show if matplotlib gets imported by the script
    import builtins, importlib
    _orig_import = builtins.__import__

    def _patched_import(name, *args, **kwargs):
        mod = _orig_import(name, *args, **kwargs)
        if name == "matplotlib.pyplot":
            try:
                import matplotlib.pyplot as plt
                _real_show = plt.show
                def _save_instead(*a, **k):
                    save_all_figs()
                    # no GUI popup
                plt.show = _save_instead
            except Exception:
                pass
        return mod

    builtins.__import__ = _patched_import

    # 4) Run the script as __main__ (no edits to trade-repo needed)
    stdio = io.StringIO()
    try:
        # Capture anything it prints (e.g., file paths)
        _orig_stdout, _orig_stderr = os.sys.stdout, os.sys.stderr
        os.sys.stdout = os.sys.stderr = stdio
        runpy.run_path(str(script_path), run_name="__main__")
    finally:
        os.sys.stdout, os.sys.stderr = _orig_stdout, _orig_stderr
        builtins.__import__ = _orig_import
        webbrowser.open = real_open
        # final safety: if any figures were created but show() never called
        save_all_figs(tag="autosaved")

    # 5) Collect outputs we can serve
    printed = stdio.getvalue()
    outputs = sorted([p.name for p in outdir.iterdir() if p.is_file()])
    return {"outputs": outputs, "opened": opened_targets, "printed": printed}