# Inspect raw FBX: axis settings, model names, local transforms, and geometry extents per model.
# usage: blender -b --factory-startup --python verify_fbx.py -- file.fbx [file2.fbx ...]
import sys, os
import bpy
from io_scene_fbx import parse_fbx
argv = sys.argv[sys.argv.index('--') + 1:]
for path in argv:
    root, ver = parse_fbx.parse(path)
    print('FILE', os.path.basename(path), 'ver', ver)
    def find(elem, id_):
        for c in elem.elems:
            if c.id == id_:
                return c
    gs = find(find(root, b'GlobalSettings'), b'Properties70')
    for p in gs.elems:
        k = p.props[0].decode()
        if k in ('UpAxis', 'UpAxisSign', 'FrontAxis', 'FrontAxisSign', 'CoordAxis', 'CoordAxisSign', 'UnitScaleFactor'):
            print('  GS', k, p.props[-1])
    objs = find(root, b'Objects')
    geo = {}
    models = {}
    for e in objs.elems:
        if e.id == b'Geometry':
            v = find(e, b'Vertices')
            arr = v.props[0] if v else []
            xs, ys, zs = arr[0::3], arr[1::3], arr[2::3]
            if len(xs):
                geo[e.props[0]] = ((min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs)))
        if e.id == b'Model':
            name = e.props[1].split(b'\x00')[0].decode()
            p70 = find(e, b'Properties70')
            tr = {}
            if p70:
                for p in p70.elems:
                    k = p.props[0].decode()
                    if k in ('Lcl Translation', 'Lcl Rotation', 'Lcl Scaling', 'PreRotation'):
                        tr[k] = tuple(round(x, 3) for x in p.props[4:7])
            models[e.props[0]] = (name, tr)
    conns = find(root, b'Connections')
    g2m = {}
    for c in conns.elems:
        a, b = c.props[1], c.props[2]
        if a in geo and b in models:
            g2m[b] = geo[a]
    for mid, (name, tr) in models.items():
        g = g2m.get(mid)
        gs_ = ' geo x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]' % (g[0] + g[1] + g[2]) if g else ''
        print('  M', name, tr, gs_)
