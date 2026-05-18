#!/usr/bin/env bash
# bootstrap_env.sh — set up an isolated Python env for the kedro-babysit skill.
#
# Two modes, picked automatically based on env state:
#
#   1. CREATE FLOW (no isolated env active): creates a new venv or conda env
#      and prints the activation command. The script CANNOT activate the env
#      from a child shell, so it exits 0 and asks the user to activate + re-run.
#
#   2. INSTALL FLOW (env is active): verifies that the binaries the skill's
#      targeted-fix recipes invoke (pytest, pre-commit, mypy, lint-imports,
#      detect-secrets-hook; and mkdocs if --with-docs) are on PATH, and runs
#      make install-test-requirements + make install-pre-commit (and
#      make install-docs-requirements if --with-docs) if any are missing.
#      Probes for system tools (gh, vale, lychee) and prints platform-specific
#      install hints if any are missing.
#
# Usage:
#   bash bootstrap_env.sh                                           # auto-detect mode
#   bash bootstrap_env.sh --type {venv|conda} --name <name>         # create flow
#   bash bootstrap_env.sh --type venv --name .venv --python 3.11    # full create
#   bash bootstrap_env.sh --with-docs                               # install flow + docs deps
#
# An isolated env is detected when:
#   - $VIRTUAL_ENV is set, OR
#   - $CONDA_PREFIX is set AND $CONDA_DEFAULT_ENV != "base".

set -euo pipefail

# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------
# Kedro supports Python 3.10-3.14 (see pyproject.toml `requires-python`).
SUPPORTED_PY_MIN=10        # i.e. 3.10
SUPPORTED_PY_MAX=14        # i.e. 3.14
DEFAULT_PY_VERSION="3.11"  # Fallback only; matches the lint job in all-checks.yml.

# [test]-extra binaries the skill's targeted-fix recipes invoke. Probed via
# `command -v` (not `python -c "import X"`) because the skill calls these as
# CLI binaries — and an importable module can still be missing its entry-point
# script (e.g. older import-linter versions registered `lint-imports` under a
# different entry point, so `import importlinter` succeeded but the binary was
# absent). Checking PATH matches what the recipes will actually do.
# (Ruff is excluded — pre-commit ships its own pinned binary in its hook cache.)
# Keep in sync with the docstring above.
REQUIRED_TEST_BINARIES="pytest pre-commit mypy lint-imports detect-secrets-hook"

TYPE=""
NAME=""
EXPLICIT_PYTHON=""         # set only if user passes --python
WITH_DOCS=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --type)
            TYPE="$2"
            shift 2
            ;;
        --name)
            NAME="$2"
            shift 2
            ;;
        --python)
            EXPLICIT_PYTHON="$2"
            shift 2
            ;;
        --with-docs)
            WITH_DOCS=1
            shift
            ;;
        -h|--help)
            sed -n '2,/^set -euo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Error: unknown argument: $1" >&2
            echo "Run with --help for usage." >&2
            exit 64
            ;;
    esac
done

if [[ -n "$TYPE" && "$TYPE" != "venv" && "$TYPE" != "conda" ]]; then
    echo "Error: --type must be 'venv' or 'conda', got: $TYPE" >&2
    exit 64
fi

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
section() {
    echo
    echo "===> $*"
}

ok()    { echo "  [OK]    $*"; }
warn()  { echo "  [WARN]  $*"; }
miss()  { echo "  [MISS]  $*"; }
info()  { echo "  [..]    $*"; }   # announcing an in-progress action; success is reported by ok() afterwards

# Extract major.minor (e.g. "3.12") from `python --version` output, or empty.
detect_python_minor() {
    local py="${1:-python}"
    "$py" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1
}

# Returns 0 if "X.Y" is in Kedro's supported range (3.SUPPORTED_PY_MIN .. 3.SUPPORTED_PY_MAX).
is_supported_python() {
    local v="$1"
    local major="${v%%.*}"
    local minor="${v#*.}"
    [[ "$major" == "3" ]] || return 1
    [[ "$minor" =~ ^[0-9]+$ ]] || return 1
    (( minor >= SUPPORTED_PY_MIN && minor <= SUPPORTED_PY_MAX ))
}

# Resolve the Python version to use for a NEW env:
#   1. If --python passed, honour it (no validation: user's choice).
#   2. Else, detect current interpreter; use it if in supported range.
#   3. Else, fall back to DEFAULT_PY_VERSION.
# Prints the chosen version and a one-line rationale to stderr.
resolve_python_version() {
    if [[ -n "$EXPLICIT_PYTHON" ]]; then
        echo "  Using --python $EXPLICIT_PYTHON (explicit)" >&2
        echo "$EXPLICIT_PYTHON"
        return
    fi
    local detected
    detected="$(detect_python_minor)"
    if [[ -n "$detected" ]] && is_supported_python "$detected"; then
        echo "  Detected Python $detected on PATH (in Kedro's supported range 3.${SUPPORTED_PY_MIN}-3.${SUPPORTED_PY_MAX}); using it" >&2
        echo "$detected"
        return
    fi
    if [[ -n "$detected" ]]; then
        echo "  Detected Python $detected (outside Kedro's supported range 3.${SUPPORTED_PY_MIN}-3.${SUPPORTED_PY_MAX})" >&2
    else
        echo "  No python interpreter detected on PATH" >&2
    fi
    echo "  Falling back to default: $DEFAULT_PY_VERSION" >&2
    echo "$DEFAULT_PY_VERSION"
}

# Detect platform for install hints
detect_platform() {
    case "$(uname -s)" in
        Darwin)         echo "macos" ;;
        Linux)          echo "linux" ;;
        MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
        *)              echo "other" ;;
    esac
}

print_install_hint() {
    local tool="$1"
    local platform
    platform="$(detect_platform)"
    case "$platform" in
        macos)
            echo "    Install: brew install $tool"
            ;;
        linux)
            case "$tool" in
                gh)     echo "    Install: sudo apt install gh  (or see https://github.com/cli/cli#installation)" ;;
                vale)   echo "    Install: download from https://github.com/errata-ai/vale/releases  (or via Linuxbrew)" ;;
                lychee) echo "    Install: cargo install lychee  (or download from https://github.com/lycheeverse/lychee/releases)" ;;
            esac
            ;;
        windows)
            case "$tool" in
                gh)     echo "    Install: download from https://github.com/cli/cli/releases" ;;
                vale)   echo "    Install: download from https://github.com/errata-ai/vale/releases" ;;
                lychee) echo "    Install: download from https://github.com/lycheeverse/lychee/releases" ;;
            esac
            ;;
        *)
            echo "    Install: see the project's GitHub releases page for $tool"
            ;;
    esac
}

# --------------------------------------------------------------------------
# Preflight: gh
# --------------------------------------------------------------------------
section "Preflight"

if command -v gh >/dev/null 2>&1; then
    if gh auth status >/dev/null 2>&1; then
        ok "gh installed and authenticated"
    else
        warn "gh installed but not authenticated. Run: gh auth login"
        warn "  (only required by watch_ci.sh — bootstrap will continue)"
    fi
else
    warn "gh not installed (only required by watch_ci.sh — bootstrap will continue)"
    print_install_hint gh
fi

# --------------------------------------------------------------------------
# Detect active env
# --------------------------------------------------------------------------
section "Active environment"

ACTIVE_ENV_KIND=""    # "venv" | "conda" | ""
ACTIVE_ENV_PATH=""

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    ACTIVE_ENV_KIND="venv"
    ACTIVE_ENV_PATH="$VIRTUAL_ENV"
elif [[ -n "${CONDA_PREFIX:-}" && "${CONDA_DEFAULT_ENV:-}" != "base" && -n "${CONDA_DEFAULT_ENV:-}" ]]; then
    ACTIVE_ENV_KIND="conda"
    ACTIVE_ENV_PATH="$CONDA_PREFIX"
fi

PYTHON_BIN="$(command -v python || command -v python3 || true)"
if [[ -n "$PYTHON_BIN" ]]; then
    PYTHON_PREFIX="$("$PYTHON_BIN" -c 'import sys; print(sys.prefix)' 2>/dev/null || echo "?")"
    PYTHON_RUNTIME_VERSION="$("$PYTHON_BIN" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))' 2>/dev/null || echo "?")"
else
    PYTHON_PREFIX="?"
    PYTHON_RUNTIME_VERSION="?"
fi

echo "  VIRTUAL_ENV         = ${VIRTUAL_ENV:-<unset>}"
echo "  CONDA_PREFIX        = ${CONDA_PREFIX:-<unset>}"
echo "  CONDA_DEFAULT_ENV   = ${CONDA_DEFAULT_ENV:-<unset>}"
echo "  python              = ${PYTHON_BIN:-<not found>}"
echo "  sys.prefix          = $PYTHON_PREFIX"
echo "  python version      = $PYTHON_RUNTIME_VERSION"
echo "  isolated env active = ${ACTIVE_ENV_KIND:-no}"

# --------------------------------------------------------------------------
# Branch: create flow OR install flow
# --------------------------------------------------------------------------

if [[ -z "$ACTIVE_ENV_KIND" ]]; then
    # =============== CREATE FLOW ===============
    section "Create flow"

    if [[ -z "$TYPE" ]]; then
        echo "  No isolated env active (refusing to use system Python or conda 'base')." >&2
        echo "  To create one, re-run with:" >&2
        echo "    bash $(basename "$0") --type venv  --name .venv             [--python X.Y]" >&2
        echo "    bash $(basename "$0") --type conda --name kedro-babysit     [--python X.Y]" >&2
        echo "  --python defaults to: current python if in 3.${SUPPORTED_PY_MIN}-3.${SUPPORTED_PY_MAX}, else $DEFAULT_PY_VERSION." >&2
        exit 64
    fi

    if [[ -z "$NAME" ]]; then
        if [[ "$TYPE" == "venv" ]]; then
            NAME=".venv"
        else
            NAME="kedro-babysit"
        fi
    fi

    PYTHON_VERSION="$(resolve_python_version)"

    RERUN_FLAGS=""
    if [[ $WITH_DOCS -eq 1 ]]; then
        RERUN_FLAGS=" --with-docs"
    fi

    case "$TYPE" in
        venv)
            if [[ -d "$NAME" ]]; then
                warn "$NAME already exists; reusing."
            elif command -v uv >/dev/null 2>&1; then
                info "Creating venv at $NAME with uv (python $PYTHON_VERSION)"
                uv venv "$NAME" --python "$PYTHON_VERSION"
            else
                warn "uv not found; falling back to 'python -m venv'"
                PY_FOR_VENV="$(command -v "python$PYTHON_VERSION" || command -v python3 || command -v python)"
                if [[ -z "$PY_FOR_VENV" ]]; then
                    echo "Error: no python interpreter found to create venv" >&2
                    exit 1
                fi
                info "Creating venv at $NAME with $PY_FOR_VENV"
                "$PY_FOR_VENV" -m venv "$NAME"
            fi
            echo
            echo "  Now activate the env and re-run this script:"
            echo "    source $NAME/bin/activate"
            echo "    bash \"$0\"$RERUN_FLAGS"
            ;;
        conda)
            if ! command -v conda >/dev/null 2>&1; then
                echo "Error: conda not found on PATH" >&2
                exit 1
            fi
            if conda env list | awk '{print $1}' | grep -qx "$NAME"; then
                warn "conda env '$NAME' already exists; reusing."
            else
                info "Creating conda env '$NAME' (python $PYTHON_VERSION)"
                conda create -y -n "$NAME" "python=$PYTHON_VERSION"
            fi
            echo
            echo "  Now activate the env and re-run this script:"
            echo "    conda activate $NAME"
            echo "    bash \"$0\"$RERUN_FLAGS"
            ;;
    esac

    exit 0
fi

# =============== INSTALL FLOW ===============
# (only reached when an isolated env is active)

# Locate repo root so make targets work regardless of cwd
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$REPO_ROOT" ]]; then
    echo "Error: not inside a git repository" >&2
    exit 1
fi

# Soft check: warn if active env's Python is outside Kedro's supported range.
# Don't refuse — the user already made their choice when activating.
ACTIVE_PY_MINOR="$(detect_python_minor "$PYTHON_BIN")"
if [[ -n "$ACTIVE_PY_MINOR" ]] && ! is_supported_python "$ACTIVE_PY_MINOR"; then
    warn "Active env Python is $ACTIVE_PY_MINOR; Kedro supports 3.${SUPPORTED_PY_MIN}-3.${SUPPORTED_PY_MAX}."
    warn "  CI will not run this version. Install may still succeed, but expect surprises."
fi

section "Python dependencies"

MISSING_BINARIES=""
for bin in $REQUIRED_TEST_BINARIES; do
    command -v "$bin" >/dev/null 2>&1 || MISSING_BINARIES="$MISSING_BINARIES $bin"
done

if [[ -z "$MISSING_BINARIES" ]]; then
    ok "all required [test] binaries on PATH: $REQUIRED_TEST_BINARIES"
else
    miss "missing binaries from [test]:$MISSING_BINARIES"
    info "Running: make install-test-requirements && make install-pre-commit"
    (cd "$REPO_ROOT" && make install-test-requirements && make install-pre-commit)
fi

if [[ $WITH_DOCS -eq 1 ]]; then
    if "$PYTHON_BIN" -c 'import mkdocs' >/dev/null 2>&1; then
        ok "mkdocs installed"
    else
        miss "mkdocs not installed"
        info "Running: make install-docs-requirements"
        (cd "$REPO_ROOT" && make install-docs-requirements)
    fi
fi

# --------------------------------------------------------------------------
# System tools probe
# --------------------------------------------------------------------------
section "System tools"

declare -i MISSING_TOOLS=0
for tool in gh vale lychee; do
    if command -v "$tool" >/dev/null 2>&1; then
        ok "$tool found at $(command -v "$tool")"
    else
        miss "$tool not found"
        print_install_hint "$tool"
        MISSING_TOOLS+=1
    fi
done

# --------------------------------------------------------------------------
# Final summary
# --------------------------------------------------------------------------
section "Summary"

echo "  Env kind            : $ACTIVE_ENV_KIND"
echo "  Env path            : $ACTIVE_ENV_PATH"
echo "  Python version      : $PYTHON_RUNTIME_VERSION"
SUMMARY_MISSING=""
for bin in $REQUIRED_TEST_BINARIES; do
    command -v "$bin" >/dev/null 2>&1 || SUMMARY_MISSING="$SUMMARY_MISSING $bin"
done
if [[ -z "$SUMMARY_MISSING" ]]; then
    echo "  Test deps           : ready"
else
    echo "  Test deps           : MISSING:$SUMMARY_MISSING (install failed?)"
fi
if [[ $WITH_DOCS -eq 1 ]]; then
    if "$PYTHON_BIN" -c 'import mkdocs' >/dev/null 2>&1; then
        echo "  Docs deps           : ready"
    else
        echo "  Docs deps           : MISSING (install failed?)"
    fi
fi
echo "  System tools missing: $MISSING_TOOLS  (skill prints hints; never installs)"
echo
if [[ $MISSING_TOOLS -gt 0 ]]; then
    echo "  Note: docs checks that depend on missing system tools will be reported as [SKIP]."
fi

exit 0
