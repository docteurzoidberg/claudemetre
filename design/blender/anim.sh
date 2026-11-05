#!/usr/bin/env bash
# Vidéo du voyant avec le Blender Windows, depuis WSL, puis encodage en MP4.
#   ./anim.sh <variante> [preview|final]
# Écrit design/renders/<variante>.mp4 (ou preview/) ; les images restent dans design/renders/anim/<variante>/.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../../prive.env"
NAME="$1"
QUALITY="${2:-preview}"
DEST="$HERE/../renders"
[ "$QUALITY" = final ] || DEST="$DEST/preview"
"$BLENDER" -b --factory-startup -P "$(wslpath -w "$HERE/anim.py")" -- "$NAME" "$QUALITY" 2>&1 \
  | grep -E "RENDERED|Error|Traceback|File \"|line [0-9]+|Exception" || true
ffmpeg -y -loglevel error -framerate 25 -i "$HERE/../renders/anim/$NAME/%04d.png" \
  -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -movflags +faststart "$DEST/$NAME.mp4"
ls -la "$DEST/$NAME.mp4"
