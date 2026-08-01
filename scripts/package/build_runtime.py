"""Build a relocatable, self-contained Python runtime for one target.

Why not the repo `.venv`: a venv records the absolute path of the interpreter it
was created from, so it breaks the moment the app is copied to another machine.
Instead we unpack an astral-sh/python-build-standalone "install_only" CPython -
which is relocatable by construction - and pip-install the project into it.

The result lands in `.cache/package/pyruntime/<target>/` and is mirrored into
`app/build-resources/pyruntime` at stage time.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .common import (
    REPO_ROOT,
    RUNTIME_CACHE,
    CACHE_DIR,
    download,
    extract,
    human,
    log,
    rmtree,
    run,
    size_of,
)
from .targets import DEPS, PBS_RELEASE, PBS_URL, PY_VERSION, PY_XY, Target, is_native

STAMP = ".aesthetician-runtime.json"
# Bump when the prune/install recipe changes so cached runtimes are rebuilt.
RECIPE = 5


# ── pruning ──────────────────────────────────────────────────────────────
# Everything here is dead weight for us: build headers, static libs, Tcl/Tk (we
# never open a Tk window), the stdlib test suite, and the numpy/scipy/opencv
# test corpora. Each entry is relative to the runtime root.
PRUNE_DIRS_COMMON = (
    "include",
    "share/man",
    "share/doc",
    "share/terminfo",
)
PRUNE_STDLIB_DIRS = (
    "test",
    "idlelib",
    "tkinter",
    "turtledemo",
    "lib2to3",
    "ensurepip",
    "pydoc_data",
    "distutils",
    "sqlite3/test",
    "unittest/test",
)
PRUNE_SITE_DIRS = (
    "pip",
    "setuptools",
    "pkg_resources",
    "wheel",
    "_distutils_hatch",
    # numpy/f2py must stay: `from numpy import *` triggers numpy.__getattr__,
    # which imports it, and scipy's array-api shim does exactly that at import.
    "numpy/distutils",
    "numpy/_core/include",
    "numpy/_core/lib",
    "numpy/random/lib",
    "numpy/_pyinstaller",
    "scipy/_lib/tests",
    "cv2/data",           # haar cascades - the engine never does detection
    "cv2/misc",
)
PRUNE_SITE_GLOBS = (
    "pip-*.dist-info",
    "setuptools-*.dist-info",
    "wheel-*.dist-info",
)
# Suffixes that only matter when compiling against these packages.
PRUNE_SUFFIXES = (".pyi", ".pyx", ".pxd", ".pxi", ".h", ".hpp", ".a", ".lib", ".exp")
KEEP_TEST_DIRS = ("numpy/testing",)


def _prune(root: Path, site: Path, keep_bytecode: bool) -> dict[str, int]:
    """Delete build-only and test-only payload. Returns {label: bytes freed}."""
    freed: dict[str, int] = {}

    def drop(p: Path, label: str) -> None:
        if not p.exists() and not p.is_symlink():
            return
        n = size_of(p)
        rmtree(p)
        freed[label] = freed.get(label, 0) + n

    for rel in PRUNE_DIRS_COMMON:
        drop(root / rel, "runtime extras")

    stdlib = root / "lib" / f"python{PY_XY}"
    if not stdlib.is_dir():                       # Windows layout
        stdlib = root / "Lib"
    for rel in PRUNE_STDLIB_DIRS:
        drop(stdlib / rel, "stdlib extras")

    # Tcl/Tk and the static libpython are pure overhead for a GUI-less engine.
    for pat in ("libpython*.a", "libtcl*", "libtk*", "tcl*", "tk*", "itcl*", "thread*"):
        for p in (root / "lib").glob(pat):
            drop(p, "tcl/tk + static libs")
    drop(root / "lib" / f"python{PY_XY}" / f"config-{PY_XY}-darwin", "static libs")
    for p in (root / "lib").glob(f"python{PY_XY}/config-*"):
        drop(p, "static libs")
    drop(root / "libs", "static libs")            # Windows .lib import libs
    drop(root / "tcl", "tcl/tk + static libs")
    for pat in ("_tkinter*", "tcl*.dll", "tk*.dll"):
        for p in (root / "DLLs").glob(pat):
            drop(p, "tcl/tk + static libs")

    for rel in PRUNE_SITE_DIRS:
        drop(site / rel, "package extras")
    for pat in PRUNE_SITE_GLOBS:
        for p in site.glob(pat):
            drop(p, "package extras")

    # Test suites shipped inside wheels (scipy alone is ~40 MB of them).
    keep = {(site / k).resolve() for k in KEEP_TEST_DIRS}
    for dirpath, dirnames, _ in os.walk(site, topdown=True):
        for name in list(dirnames):
            if name in ("tests", "test"):
                p = Path(dirpath) / name
                if p.resolve() in keep:
                    continue
                dirnames.remove(name)
                drop(p, "package test suites")

    # Header/stub/static-lib leftovers anywhere in the runtime.
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(PRUNE_SUFFIXES):
                drop(Path(dirpath) / name, "headers/stubs")

    if not keep_bytecode:
        for dirpath, dirnames, _ in os.walk(root, topdown=True):
            for name in list(dirnames):
                if name == "__pycache__":
                    dirnames.remove(name)
                    drop(Path(dirpath) / name, "__pycache__")

    return freed


# ── project wheel ────────────────────────────────────────────────────────
def _project_wheel(builder_python: str) -> Path:
    """Build (and cache) a pure-python wheel of the aesthetician package."""
    wheel_dir = CACHE_DIR / "wheels"
    wheel_dir.mkdir(parents=True, exist_ok=True)
    # Rebuild whenever any source file is newer than the cached wheel.
    existing = sorted(wheel_dir.glob("aesthetician-*.whl"))
    newest_src = max(
        (p.stat().st_mtime for p in REPO_ROOT.joinpath("aesthetician").rglob("*.py")),
        default=0.0,
    )
    newest_src = max(newest_src, REPO_ROOT.joinpath("pyproject.toml").stat().st_mtime)
    if existing and existing[-1].stat().st_mtime >= newest_src:
        log(f"cached  {existing[-1].name}")
        return existing[-1]
    for p in existing:
        p.unlink()
    log("build   aesthetician wheel")
    run([builder_python, "-m", "pip", "wheel", "--no-deps", "--no-cache-dir",
         "-w", wheel_dir, REPO_ROOT])
    built = sorted(wheel_dir.glob("aesthetician-*.whl"))
    if not built:
        raise SystemExit("failed to build the aesthetician wheel")
    return built[-1]


def _cross_pip_args(target: Target) -> list[str]:
    args = ["--only-binary=:all:", "--python-version", PY_VERSION,
            "--implementation", "cp", "--abi", f"cp{PY_XY.replace('.', '')}"]
    for plat in target.pip_platforms:
        args += ["--platform", plat]
    return args


def _project_version() -> str:
    txt = (REPO_ROOT / "pyproject.toml").read_text()
    for line in txt.splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("could not read version from pyproject.toml")


def _install(target: Target, root: Path, native: bool, builder_python: str) -> None:
    site = root / target.site_rel
    py = root / target.python_rel
    wheel = _project_wheel(builder_python)

    if native:
        # The bundled interpreter resolves its own wheels - always correct.
        log(f"pip install (native) into {root.name}")
        run([py, "-m", "pip", "install", "--no-warn-script-location",
             "--no-cache-dir", "--upgrade", *DEPS])
        run([py, "-m", "pip", "install", "--no-warn-script-location",
             "--no-cache-dir", "--upgrade", "--no-deps", wheel])
    else:
        # Cross target: we cannot execute that interpreter, so resolve wheels by
        # platform tag and drop them straight into its site-packages.
        log(f"pip install (cross, {'/'.join(target.pip_platforms)}) into {root.name}")
        site.mkdir(parents=True, exist_ok=True)
        run([builder_python, "-m", "pip", "install", "--no-warn-script-location",
             "--no-cache-dir", "--upgrade", "--target", site,
             *_cross_pip_args(target), *DEPS])
        run([builder_python, "-m", "pip", "install", "--no-warn-script-location",
             "--no-cache-dir", "--upgrade", "--no-deps", "--target", site, wheel])



def _install_project_only(target: Target, root: Path, native: bool, builder_python: str) -> None:
    """Reinstall just this project into an otherwise-cached runtime.

    The cache stamp deliberately tracks only the expensive, slow-moving pieces
    (CPython, the third-party wheels). Our own package changes on nearly every
    build, so it is always reinstalled: a cache hit that kept a stale
    aesthetician/ shipped an app whose Info.plist said one version while its
    engine was an older one, which is very hard to spot from the outside.
    """
    site = root / target.site_rel
    py = root / target.python_rel
    wheel = _project_wheel(builder_python)
    log("pip install (project only, cache refresh)")
    if native:
        run([py, "-m", "pip", "install", "--no-warn-script-location", "--no-cache-dir",
             "--force-reinstall", "--no-deps", wheel])
    else:
        run([builder_python, "-m", "pip", "install", "--no-warn-script-location",
             "--no-cache-dir", "--force-reinstall", "--no-deps", "--target", site,
             *_cross_pip_args(target), wheel])
    # Fresh sources need fresh hash-based caches, or the app writes .pyc into its
    # own signed bundle at runtime and macOS then refuses to launch it.
    pkg = site / "aesthetician"
    if pkg.is_dir():
        compiler = str(py) if native else builder_python
        subprocess.run([compiler, "-m", "compileall", "-q", "-j", "0", "-f",
                        "--invalidation-mode", "unchecked-hash", str(pkg)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _compile_bytecode(root: Path, target: Target, native: bool, builder_python: str) -> None:
    """Precompile to .pyc so the GUI's per-action python spawns start fast.

    The bundle is read-only in practice (writing into a signed .app breaks its
    seal), so without this every launch re-parses numpy/scipy/cv2 from source.
    """
    py = str(root / target.python_rel) if native else builder_python
    stdlib = root / "lib" / f"python{PY_XY}"
    targets = [stdlib] if stdlib.is_dir() else [root / "Lib"]
    site = root / target.site_rel
    if site.is_dir():
        targets.append(site)
    log("compileall (bytecode cache, unchecked-hash)")
    for t in targets:
        # unchecked-hash: the .pyc records a source hash and is trusted without
        # comparing mtimes. Timestamp caches would be invalidated the moment
        # electron-builder copies the tree, and Python would then rewrite them at
        # runtime -- writing inside a signed .app breaks its seal and macOS
        # refuses to launch it next time.
        # Not all sources compile cleanly across versions; -q and no check.
        subprocess.run([py, "-m", "compileall", "-q", "-j", "0", "-f",
                        "--invalidation-mode", "unchecked-hash", str(t)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ── verification ─────────────────────────────────────────────────────────
def engine_counts(python: str | Path, root_env: dict[str, str],
                  launcher: list[str] | None = None) -> tuple[int, int]:
    """Ask an interpreter for its effect/preset counts via the real CLI path."""
    # cwd MUST be outside the repo: python puts the working directory on sys.path,
    # so running this from the checkout imports the dev tree and the bundle's own
    # site-packages is never exercised. That mistake once shipped an app whose
    # engine was a version behind while every check passed.
    cmd = (launcher or []) + [str(python), "-m", "aesthetician.cli", "schema"]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=root_env,
                          cwd=tempfile.gettempdir(), timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"schema failed: {proc.stderr[-2000:]}")
    data = json.loads(proc.stdout)
    return len(data["effects"]), len(data["presets"])


def assert_bundled_engine(python: str | Path, root: Path, root_env: dict[str, str],
                          launcher: list[str] | None = None) -> str:
    """Confirm the interpreter imports the engine FROM THE BUNDLE, at our version."""
    code = ("import aesthetician,sys;"
            "sys.stdout.write(aesthetician.__file__+'|'+aesthetician.__version__)")
    proc = subprocess.run((launcher or []) + [str(python), "-c", code],
                          capture_output=True, text=True, env=root_env,
                          cwd=tempfile.gettempdir(), timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"engine import failed: {proc.stderr[-2000:]}")
    path, version = proc.stdout.strip().split("|")
    if str(root.resolve()) not in str(Path(path).resolve()):
        raise RuntimeError(
            f"bundled engine resolved OUTSIDE the runtime: {path}\n"
            "the check was not exercising the bundle")
    expected = _project_version()
    if version != expected:
        raise RuntimeError(
            f"bundled engine is version {version}, expected {expected} - "
            "the cached runtime kept a stale copy of the project")
    return version


def source_counts() -> tuple[int, int]:
    """How many effects and presets the source tree declares.

    Counted by parsing rather than importing: this runs on the build host, which
    has no obligation to have the engine or numpy/scipy/OpenCV installed. The
    registrations are plain, unconditional module-level declarations - a
    `@register`-decorated class per effect, a `register_preset(...)` call per
    preset - so the AST is an exact count, not an estimate.
    """
    def scan(pkg: str, pred) -> int:
        total = 0
        for path in (REPO_ROOT / "aesthetician" / pkg).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            total += sum(1 for node in ast.walk(ast.parse(path.read_text())) if pred(node))
        return total

    def is_effect(node) -> bool:
        if not isinstance(node, ast.ClassDef):
            return False
        return any(getattr(d.func if isinstance(d, ast.Call) else d, "id", "") == "register"
                   for d in node.decorator_list)

    def is_preset(node) -> bool:
        return isinstance(node, ast.Call) and getattr(node.func, "id", "") == "register_preset"

    return scan("effects", is_effect), scan("presets", is_preset)


def verify(target: Target, root: Path, ffmpeg_dir: Path | None, assets: Path | None,
           expect: tuple[int, int] | None = None) -> str:
    """Run the bundled interpreter and confirm dynamic discovery still works.

    The bundle has to find exactly what the source declares. Comparing against
    the source rather than a number written down here is the point: the counts
    move every time a preset lands, and a hardcoded pair turns "someone added a
    preset" into a failed release build - which is precisely what it did.
    """
    native = is_native(target)
    launcher: list[str] | None = None
    if not native:
        if target.key == "mac-x64" and sys.platform == "darwin" and shutil.which("arch"):
            # Rosetta 2 lets us smoke-test the x86_64 runtime on Apple silicon.
            probe = subprocess.run(["arch", "-x86_64", "/usr/bin/true"], capture_output=True)
            if probe.returncode == 0:
                launcher = ["arch", "-x86_64"]
    if not native and launcher is None:
        # Windows from macOS: structural check only.
        site = root / target.site_rel
        missing = [m for m in ("numpy", "scipy", "cv2", "click", "rich", "requests",
                               "aesthetician") if not (site / m).exists()]
        if missing:
            raise SystemExit(f"{target.key}: missing packages in site-packages: {missing}")
        pyds = list((site / "cv2").glob("*.pyd")) + list((site / "numpy").rglob("*.pyd"))
        if not pyds:
            raise SystemExit(f"{target.key}: no .pyd extensions found - wrong wheels?")
        return "structural only (cannot execute this target here)"

    env = {"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "/tmp")}
    if ffmpeg_dir:
        env["AESTHETICIAN_FFMPEG"] = str(ffmpeg_dir / f"ffmpeg{target.exe_suffix}")
        env["AESTHETICIAN_FFPROBE"] = str(ffmpeg_dir / f"ffprobe{target.exe_suffix}")
    if assets:
        env["AESTHETICIAN_ASSETS"] = str(assets)
    version = assert_bundled_engine(root / target.python_rel, root, env, launcher)
    n_eff, n_pre = engine_counts(root / target.python_rel, env, launcher)
    want = expect if expect is not None else source_counts()
    if (n_eff, n_pre) != want:
        raise SystemExit(
            f"{target.key}: bundled runtime reports {n_eff} effects / {n_pre} presets, "
            f"but the source declares {want[0]}/{want[1]} - either dynamic module "
            "discovery is broken or the prune step removed something it should not have"
        )
    how = "native" if native else "under Rosetta"
    return f"v{version}, {n_eff} effects, {n_pre} presets ({how})"


# ── entry point ──────────────────────────────────────────────────────────
def build(target: Target, *, force: bool = False, bytecode: bool = True,
          builder_python: str | None = None) -> Path:
    root = RUNTIME_CACHE / target.key
    stamp_path = root / STAMP
    want = {
        "recipe": RECIPE,
        "python": PY_VERSION,
        "pbs": PBS_RELEASE,
        "deps": sorted(DEPS),
        "bytecode": bytecode,
    }
    if not force and stamp_path.is_file():
        try:
            if json.loads(stamp_path.read_text()) == want:
                log(f"runtime cached: {target.key} ({human(size_of(root))})")
                native = is_native(target)
                _install_project_only(
                    target, root, native,
                    builder_python or (str(root / target.python_rel) if native else sys.executable),
                )
                return root
        except Exception:
            pass

    url = PBS_URL.format(rel=PBS_RELEASE, ver=PY_VERSION, triple=target.pbs_triple)
    tarball = download(url, f"cpython-{PY_VERSION}+{PBS_RELEASE}-{target.pbs_triple}.tar.gz")

    staging = RUNTIME_CACHE / f".{target.key}.extract"
    extract(tarball, staging)
    inner = staging / "python"
    if not inner.is_dir():
        raise SystemExit(f"unexpected archive layout in {tarball.name}")
    rmtree(root)
    root.parent.mkdir(parents=True, exist_ok=True)
    inner.rename(root)
    rmtree(staging)

    native = is_native(target)
    builder_python = builder_python or (
        str(root / target.python_rel) if native else sys.executable
    )
    _install(target, root, native, builder_python)

    before = size_of(root)
    if bytecode:
        _compile_bytecode(root, target, native, builder_python)
    freed = _prune(root, root / target.site_rel, keep_bytecode=bytecode)
    after = size_of(root)
    for label, n in sorted(freed.items(), key=lambda kv: -kv[1]):
        log(f"pruned  {label:<22} {human(n)}")
    log(f"runtime {target.key}: {human(before)} -> {human(after)}")

    stamp_path.write_text(json.dumps(want, indent=2))
    return root
