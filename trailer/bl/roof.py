import os, sys, bpy, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import city

N = 96
sc = reset(samples=int(sys.argv[2]) if len(sys.argv) > 2 else 12)
sc.render.resolution_x, sc.render.resolution_y = 576, 1024
world_gradient((0.004, 0.012, 0.05), (0.55, 0.22, 0.12), strength=1.0)
top = city.build_city()
light('SUN', (0, 0, 100), 0.25, (0.6, 0.7, 1.0), size=3, rot=(math.radians(60), 0, math.radians(30)))
P = (-60, -560, 215.0)   # terrace floor point where he stands
# terrace slab + railing behind him
cube((P[0], P[1] + 2, P[2] - 0.15), (12, 8, 0.3), mat('slab', (0.05, 0.05, 0.05), 0.3, 0.3))
cube((P[0], P[1] + 1.2, P[2] + 1.05), (12, 0.04, 0.05), mat('rail', (0.8, 0.6, 0.3), 1, 0.2))
cube((P[0], P[1] + 1.2, P[2] + 0.52), (12, 0.02, 1.0), mat('railglass', (0.6, 0.7, 0.8), 0, 0.05, alpha=0.15))
top_z = P[2] + 1.78
card, _ = image_plane(SP + '/seq_night/0001.png', (P[0], P[1], top_z - 0.44), 0.88, seq_len=N, emit=1.0, name='him')
look0 = (P[0], P[1], top_z - 0.36)
cam = camera((P[0] - 0.5, P[1] - 2.2, top_z - 0.3), look0, lens=70, dof=2.2, fstop=1.4)
key_cam(cam, [
    (1, (P[0] - 0.55, P[1] - 2.25, top_z - 0.32), (P[0] + 0.02, P[1], top_z - 0.38), 2.26),
    (N, (P[0] - 0.12, P[1] - 1.25, top_z - 0.2), (P[0] - 0.02, P[1], top_z - 0.24), 1.26),
])
for fc in cam.animation_data.action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'
mist_output(SP + '/r/roof', 150, 3200)
city.dump_horizon(SP + '/r/roof_horizon.json', 1, N)
only = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else None
render_range(SP + '/r/roof', 1, N, only)
