#!/bin/bash
# Rebuild every asset, export FBX to Unity, render previews and compose sheets.  (run from art/blender)
set -e
cd "$(dirname "$0")"
B="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
S=$(wslpath -w "$PWD")
"$B" -b --factory-startup --python "$S\\build_all.py" | grep -E "ASSET|DONE|Error"
BL="$(wslpath -w ../blend/ouat_ch1_assets.blend)"
mkdir -p ../renders/raw/thumbs
for sh in lineup hero thumbs village_overview village_fall village_plaza village_pond; do
  "$B" -b "$BL" --python "$S\\render_previews.py" -- shot=$sh samples=${SAMPLES:-32} | grep -E "RENDERED|Error"
done
python3 compose_previews.py
