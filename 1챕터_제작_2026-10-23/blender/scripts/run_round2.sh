#!/bin/bash
# Round 2: build + export everything (incl. dressing kit, FX, Level_Ch1), layout file, game-camera renders, sheets.
set -e
cd "$(dirname "$0")"
B="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
S=$(wslpath -w "$PWD")
"$B" -b --factory-startup --python "$S\\build_all.py" | grep -E "ASSET|DONE|Traceback"
"$B" -b --factory-startup --python "$S\\make_layout.py" | grep -E "LAYOUT|SKIP"
BL="$(wslpath -w ../blend/ouat_ch1_assets.blend)"
for sh in top a_fall a_gate a_cart a_plaza a_alley a_field eye_plaza eye_gate; do
  "$B" -b "$BL" --python "$S\\game_scene.py" -- shot=$sh samples=${SAMPLES:-32} | grep -E "RENDERED|Traceback"
done
"$B" -b "$BL" --python "$S\\render_previews.py" -- shot=thumbs groups=dressing samples=24 | grep -E "RENDERED|Traceback"
python3 compose_previews.py level_top pages eye_plaza eye_gate dressing
# slice 1 (10/23): a_fall / a_gate dioramas from the exact game camera + layout json + sheets
for a in "a_fall 0" "a_fall 1" "a_fall 2" "a_fall 3" "a_gate 0" "a_gate 1" "a_gate 2" "top 0"; do set -- $a
  "$B" -b "$BL" --python "$S\\slice_scene.py" -- area=$1 shots=$2 samples=${SAMPLES:-32} | grep -E "RENDERED|Traceback"
done
"$B" -b --factory-startup --python-expr "import sys; sys.path.insert(0, r'$S'); import bpy, ouat_slice as SL; SL.write_layout_json(); SL.patch_dressing_json()"
python3 compose_slice.py
