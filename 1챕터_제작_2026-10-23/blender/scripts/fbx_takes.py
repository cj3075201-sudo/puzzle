# Print AnimStack (take) names + root model transforms straight from FBX files (no Blender import conversions).
# usage: blender -b --factory-startup --python fbx_takes.py -- a.fbx [b.fbx ...]
import sys, os
from io_scene_fbx import parse_fbx
for path in sys.argv[sys.argv.index('--') + 1:]:
    root, ver = parse_fbx.parse(path)
    objs = [e for e in root.elems if e.id == b'Objects'][0]
    stacks = []
    models = []
    for e in objs.elems:
        if e.id == b'AnimationStack':
            nm = e.props[1].split(b'\x00')[0].decode()
            stop = None
            for p in e.elems:
                if p.id == b'Properties70':
                    for q in p.elems:
                        if q.props[0] in (b'LocalStop',):
                            stop = round(q.props[-1] / 46186158000 * 30, 2)
            stacks.append((nm, stop))
        if e.id == b'Model':
            nm = e.props[1].split(b'\x00')[0].decode()
            kind = e.props[2].decode()
            tr = {}
            for p in e.elems:
                if p.id == b'Properties70':
                    for q in p.elems:
                        k = q.props[0].decode()
                        if k in ('Lcl Rotation', 'Lcl Scaling', 'PreRotation'):
                            tr[k] = tuple(round(x, 3) for x in q.props[4:7])
            models.append((nm, kind, tr))
    print('FILE', os.path.basename(path))
    print('  TAKES', stacks)
    for m in models:
        if m[2]:
            print('  MODEL', m)
    print('  MODEL names', [m[0] for m in models])
