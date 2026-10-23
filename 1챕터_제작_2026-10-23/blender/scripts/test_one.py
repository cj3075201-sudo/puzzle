# usage: blender -b --factory-startup --python test_one.py -- module func [func...] out.png [camdist]
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, bpy, math
from mathutils import Vector
import ouat_lib as L, ouat_render as R
argv = sys.argv[sys.argv.index('--') + 1:]
mod = importlib.import_module(argv[0])
funcs = argv[1:-1]
out = argv[-1]
L.reset_scene()
assets = []
x = 0
for fn in funcs:
    A = getattr(mod, fn)()
    mn, mx = A.bounds()
    w = mx.x - mn.x
    A.root.location.x = x - mn.x
    x += w + 0.4
    assets.append(A)
    n, per = A.tris()
    print('TRIS', A.name, n, per, 'size', tuple(round(v, 2) for v in (mx - mn)))
bpy.context.view_layer.update()
R.setup_render(res=(1400, 1000), samples=16, bg=L.hex2rgb('F1EEE6'))
R.prepare_all()
R.add_sun((50, 0, -35), 3.2)
R.world_light(L.hex2rgb('F1EEE6'), 0.35)
# frame all
mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
for A in assets:
    a, b = A.bounds()
    mn = Vector(map(min, mn, a)); mx = Vector(map(max, mx, b))
c = (mn + mx) / 2
size = max((mx - mn).x, (mx - mn).z * 1.4)
d = Vector((0.35, -1.0, 0.32)).normalized() * size * 1.55
cam = R.add_camera(c + d, c, lens=50)
R.render(out)
