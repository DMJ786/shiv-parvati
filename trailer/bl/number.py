import os, sys, bpy, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

random.seed(4)
N = 72
sc = reset(samples=int(sys.argv[2]) if len(sys.argv) > 2 else 16)
sc.render.resolution_x, sc.render.resolution_y = 576, 1024
world_color((0.0, 0.0, 0.0), 0)

gold = mat('gold', (1.0, 0.72, 0.32), 1.0, 0.18)
floor = mat('floor', (0.005, 0.005, 0.006), 0.0, 0.08, coat=1.0)
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0)); bpy.context.object.data.materials.append(floor)

txt = text3d('$0', (-1.72, 0, 0.3), 0.5, gold, font='/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf',
             extrude=0.08, bevel=0.014, align='LEFT', rot=(math.radians(90), 0, 0))
txt.data.space_character = 0.95

# coins raining in the background (thin gold cylinders)
coins = []
coin_mat = mat('coin', (1.0, 0.7, 0.3), 1.0, 0.25)
for i in range(70):
    x = random.uniform(-7, 7); y = random.uniform(3, 14); z0 = random.uniform(2, 12)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.035, vertices=32, location=(x, y, z0))
    c = bpy.context.object; c.data.materials.append(coin_mat)
    c.rotation_euler = (random.uniform(0, 6), random.uniform(0, 6), 0)
    spd = random.uniform(1.2, 2.2)
    rx, ry = random.uniform(-4, 4), random.uniform(-4, 4)
    for f in (1, N):
        t = (f - 1) / 24
        c.location.z = z0 - spd * t * 0.55  # slow motion fall
        if c.location.z < 0.02: c.location.z = 0.02
        c.rotation_euler = (c.rotation_euler[0] + rx * t * 0.3 if f > 1 else c.rotation_euler[0], c.rotation_euler[1] + ry * t * 0.3 if f > 1 else c.rotation_euler[1], 0)
        c.keyframe_insert('location', frame=f); c.keyframe_insert('rotation_euler', frame=f)
    for fc in c.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    coins.append(c)
# a pile of coins on the floor behind
for i in range(160):
    r = random.uniform(0, 3.5) ** 1.2; a = random.uniform(0, 6.28)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.035, vertices=24,
                                        location=(r * math.cos(a) * 1.6, 5 + r * math.sin(a), 0.02 + random.uniform(0, 0.3) * max(0, 1 - r / 3.5)))
    c = bpy.context.object; c.data.materials.append(coin_mat)
    c.rotation_euler = (random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4), 0)

# lights: big soft reflectors for the gold, a rim from behind, a sweep that glints across the digits
light('AREA', (0, -13, 4.5), 2600, (1.0, 0.85, 0.65), size=8, target=(0, 0, 0.3))
light('AREA', (-5, -2, 1.2), 250, (1.0, 0.7, 0.45), size=3, target=(0, 0, 0.3))
# (no rim light: its reflection shows in the floor)
sweep = light('AREA', (-6, 1.2, 1.0), 1200, (1.0, 0.95, 0.85), size=0.6, target=(0, 0, 0.3))
sweep.data.shape = 'RECTANGLE'; sweep.data.size = 0.25; sweep.data.size_y = 2
for f, x in ((46, -6), (68, 6)):
    sweep.location.x = x; sweep.keyframe_insert('location', frame=f)
light('SPOT', (0, 6, 8), 2500, (1.0, 0.75, 0.4), size=0.5, target=(0, 5, 0), spot=50)

cam = camera((-2.4, -1.2, 0.15), (-1.2, 0, 0.3), lens=35, dof=1.7, fstop=1.4)
key_cam(cam, [
    (1, (-2.3, -0.9, 0.16), (-1.3, 0, 0.32), 1.35),
    (40, (-1.3, -2.5, 0.27), (-0.9, 0, 0.32), 2.55),
    (72, (-0.61, -4.7, 0.42), (-0.61, 0, 0.34), 4.7),
])
for fc in cam.animation_data.action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'


def body(f):
    p = min(1.0, (f - 1) / 48)
    p = 1 - (1 - p) ** 3
    v = int(round(1_000_000_000 * p ** 1.3))
    if f >= 49: v = 1_000_000_000
    elif v > 0:
        # keep the spinning low digits alive
        v = v - v % 7 + random.randint(0, 6)
    return f'${v:,}'


outdir = SP + '/r/number'
os.makedirs(outdir, exist_ok=True)
only = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else range(1, N + 1)
sc.frame_start, sc.frame_end = 1, N
for f in only:
    p = f'{outdir}/{f:04d}.png'
    if os.path.exists(p) and len(sys.argv) <= 3: continue
    txt.data.body = body(f)
    sc.frame_set(f)
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
