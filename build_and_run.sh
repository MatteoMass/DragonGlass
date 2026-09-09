#!/usr/bin/env bash
#
# Build the frontend, then serve it together with the API — one process for both.
#
# Installs what is missing before it starts: the npm dependencies when
# node_modules is absent or older than the lock file, and the Poetry environment
# when the project has never been installed.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

FRONTEND="$ROOT/src/frontend"
CONFIG="${DRAGONGLASS_CONFIG_FILE:-$ROOT/dragonglass.yml}"

BUILD=1
RELOAD=0
HOST=""
PORT=""

usage() {
    cat <<'USAGE'
Usage: ./build_and_run.sh [options]

Builds the frontend and serves it with the API on one port.

  --no-build     Skip the frontend build and serve the current dist/.
  --reload       Restart the backend when the Python sources change.
  --port <n>     Serve on another port. Default 8017.
  --host <addr>  Bind elsewhere — 0.0.0.0 to accept from the network.
  --help         Print this.

The address comes from server.host and server.port in dragonglass.yml, or from
DRAGONGLASS_HOST and DRAGONGLASS_PORT; the flags win over both.
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-build) BUILD=0; shift ;;
        --reload)   RELOAD=1; shift ;;
        --port)     PORT="${2:?--port needs a number}"; shift 2 ;;
        --host)     HOST="${2:?--host needs an address}"; shift 2 ;;
        --help|-h)  usage; exit 0 ;;
        *)          echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

require() {
    command -v "$1" >/dev/null 2>&1 || { echo "$1 is needed and was not found." >&2; exit 1; }
}

# Read one "section.key" out of the YAML config, printing nothing when it is
# absent — which is how a default in src/config.py stays the default.
read_config() {
    [[ -f "$CONFIG" ]] || return 0
    python3 - "$CONFIG" "$1" <<'PY' 2>/dev/null || true
import sys
try:
    import yaml
except ModuleNotFoundError:
    sys.exit(0)
try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
except Exception:
    sys.exit(0)
section, _, key = sys.argv[2].partition(".")
value = (document.get(section) or {}).get(key)
if value is not None:
    print(value)
PY
}

require python3
require poetry

if [[ $BUILD -eq 1 ]]; then
    require npm
    if [[ ! -d "$FRONTEND/node_modules" || "$FRONTEND/package-lock.json" -nt "$FRONTEND/node_modules" ]]; then
        echo "==> Installing the frontend dependencies"
        if [[ -f "$FRONTEND/package-lock.json" ]]; then
            npm --prefix "$FRONTEND" ci
        else
            npm --prefix "$FRONTEND" install
        fi
    fi
    echo "==> Building the frontend"
    npm --prefix "$FRONTEND" run build
else
    echo "==> Skipping the frontend build"
fi

if ! poetry env info --path >/dev/null 2>&1; then
    echo "==> Installing the Python environment"
    poetry install
fi

# The flags win over the environment, which wins over the file, which falls
# back to what src/config.py already defaults to.
HOST="${HOST:-${DRAGONGLASS_HOST:-$(read_config server.host)}}"
PORT="${PORT:-${DRAGONGLASS_PORT:-$(read_config server.port)}}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8017}"

ARGS=(uvicorn backend:app --app-dir src --host "$HOST" --port "$PORT")
[[ $RELOAD -eq 1 ]] && ARGS+=(--reload --reload-dir src)

echo "==> Dragon Glass on http://${HOST}:${PORT} (docs at /docs)"
exec poetry run "${ARGS[@]}"
