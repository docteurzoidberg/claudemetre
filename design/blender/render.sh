#!/usr/bin/env bash
# Rend une variante avec le Blender Windows, depuis WSL.
#   ./render.sh <variante> [preview|final]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../../prive.env"
mkdir -p "$HERE/scenes"
"$BLENDER" -b --factory-startup -P "$(wslpath -w "$HERE/render.py")" -- "$@" 2>&1 \
  | grep -E "FIT|RENDERED|Error|Traceback|File \"|line [0-9]+|Exception|Warning: .*not|Saved" || true
