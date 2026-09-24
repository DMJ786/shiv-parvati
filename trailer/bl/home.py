import os, sys, bpy, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

random.seed(21)
N = 96
sc = reset(samples=int(sys.argv[2]) if len(sys.argv) > 2 else 20)
sc.render.resolution_x, sc.render.resolution_y = 576, 1024
world_gradient((0.01, 0.025, 0.09), (0.75, 0.32, 0.18), strength=0.8)


def glass_mat(name, refl=0.18, tint=(1, 1, 1)):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); tr.inputs[0].default_value = (*tint, 1)
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.02
    fr = nt.nodes.new('ShaderNodeLayerWeight'); fr.inputs[0].default_value = 0.25
    mx = nt.nodes.new('ShaderNodeMixShader')
    mp = nt.nodes.new('ShaderNodeMapRange'); mp.inputs[3].default_value = refl * 0.5; mp.inputs[4].default_value = 0.9
    nt.links.new(fr.outputs['Fresnel'], mp.inputs[0]); nt.links.new(mp.outputs[0], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o.inputs[0])
    return m


concrete = mat('concrete', (0.55, 0.53, 0.5), 0, 0.7)
dark = mat('darkmetal', (0.02, 0.02, 0.02), 0.8, 0.35)
wood = mat('wood', (0.35, 0.18, 0.08), 0, 0.45)
plaster = mat('plaster', (0.75, 0.62, 0.48), 0, 0.8)
glass = glass_mat('glass')

# terrain
grass = mat('grass', (0.03, 0.06, 0.025), 0, 0.9)
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0)); bpy.context.object.data.materials.append(grass)
# ---- house (front face at y=0, ground floor z 0.3..3.5)
cube((0, 4, 0.15), (18, 9, 0.3), concrete)                         # plinth
cube((0, 7.9, 1.9), (14, 0.2, 3.2), plaster)                        # interior back wall
cube((0, 4, 0.31), (14, 8, 0.02), wood)                             # interior floor
cube((-7, 4, 1.9), (0.2, 8, 3.2), plaster); cube((7, 4, 1.9), (0.2, 8, 3.2), plaster)
cube((0, 4, 3.6), (14.4, 8.4, 0.25), concrete)                      # ceiling slab
# glass front with mullions
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.02, 1.9), rotation=(math.radians(90), 0, 0))
g = bpy.context.object; g.scale = (14, 3.2, 1); g.data.materials.append(glass)
for x in (-7, -3.5, 3.5, 7):
    cube((x, 0.0, 1.9), (0.08, 0.1, 3.2), dark)
cube((0, 0.0, 0.34), (14, 0.1, 0.06), dark); cube((0, 0.0, 3.47), (14, 0.1, 0.06), dark)
# upper floor: cantilevered box, wood slats + lit ribbon window
cube((2.5, 3.2, 5.2), (11, 7.5, 3.0), concrete)
cube((2.5, -0.56, 5.2), (11.02, 0.02, 3.02), mat('upperface', (0.6, 0.58, 0.55), 0, 0.6))
warmwin = emission_mat('warmwin', (1.0, 0.62, 0.3), 3.0)
cube((3.5, -0.6, 5.1), (7.5, 0.04, 1.3), warmwin)
for k in range(28):
    cube((-2.4 + k * 0.28, -0.66, 5.1), (0.06, 0.08, 1.3), wood)
cube((2.5, 3.2, 6.78), (11.6, 8.1, 0.18), concrete)
# roof edge line light
cube((2.5, -0.9, 6.7), (11.6, 0.05, 0.04), emission_mat('edge', (1.0, 0.7, 0.4), 6))

# ---- interior: dining table, pendant lamps, family silhouettes
cube((0, 3.3, 1.05), (2.8, 1.1, 0.06), wood)                        # table top (z ~1.08 incl plinth .3)
for x in (-1.2, 1.2):
    cube((x, 3.3, 0.68), (0.08, 0.9, 0.72), dark)
pend = emission_mat('pendant', (1.0, 0.72, 0.4), 40)
for x in (-0.8, 0, 0.8):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14, location=(x, 3.3, 2.35)); bpy.context.object.data.materials.append(pend)
    cube((x, 3.3, 2.95), (0.01, 0.01, 1.1), dark)
    light('POINT', (x, 3.3, 2.3), 120, (1.0, 0.7, 0.4), size=0.15)
light('AREA', (0, 7.0, 3.2), 350, (1.0, 0.65, 0.35), size=5, target=(0, 7.9, 1.5))   # wall wash
# candles on table
for x in (-0.4, 0.4):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03, location=(x, 3.3, 1.2)); bpy.context.object.data.materials.append(emission_mat('flame', (1, 0.6, 0.2), 60))
# silhouettes: (file, x, y, scale)
fam = [('grandpa', -1.75, 3.35, 0.95), ('kid2', -0.9, 4.05, 0.6), ('dad', 0.05, 4.1, 1.0), ('mom', 0.85, 4.05, 0.92),
       ('grandma', 1.75, 3.35, 0.9), ('kid1', -0.4, 2.55, 0.66)]
for name, x, y, s in fam:
    h = 0.95 * s
    card, _ = image_plane(SP + f'/sil/{name}.png', (x, y, 0.95 + h / 2 - 0.12 * s), h, emit=1.0, name=name)
# some interior props: sofa & plant silhouettes on the left, shelf light
cube((-5, 5.5, 0.6), (2.6, 1.0, 0.6), mat('sofa', (0.25, 0.22, 0.2), 0, 0.9))
cube((5, 7.6, 1.6), (2.5, 0.3, 0.04), emission_mat('shelf', (1, 0.75, 0.45), 8))

# ---- pool (in front of the house)
water = mat('water', (0.02, 0.1, 0.12), 0.0, 0.03)
wn = water.node_tree
bsdf = wn.nodes['Principled BSDF']
noise = wn.nodes.new('ShaderNodeTexNoise'); noise.noise_dimensions = '4D'; noise.inputs['Scale'].default_value = 2.0
bump = wn.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.15
wn.links.new(noise.outputs['Fac'], bump.inputs['Height']); wn.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
noise.inputs['W'].default_value = 0; noise.inputs['W'].keyframe_insert('default_value', frame=1)
noise.inputs['W'].default_value = 2.5; noise.inputs['W'].keyframe_insert('default_value', frame=N)
bsdf.inputs['Emission Color'].default_value = (0.1, 0.55, 0.7, 1); bsdf.inputs['Emission Strength'].default_value = 0.35
cube((0, -5.5, 0.04), (10, 7, 0.02), water)
deck = mat('deck', (0.3, 0.16, 0.08), 0, 0.5)
cube((0, -1.2, 0.05), (18, 1.6, 0.1), deck)
cube((-5.8, -5.5, 0.05), (1.6, 7, 0.1), deck); cube((5.8, -5.5, 0.05), (1.6, 7, 0.1), deck)
# garden bollard lights
boll = emission_mat('boll', (1.0, 0.7, 0.4), 15)
for x in (-8, -6.5, 6.5, 8):
    for y in (-2.5, -6, -9.5):
        cube((x, y, 0.3), (0.12, 0.12, 0.6), dark)
        cube((x, y, 0.62), (0.13, 0.13, 0.05), boll)
# background trees (dark, soft)
tree = mat('tree', (0.01, 0.015, 0.01), 0, 0.9)
for i in range(22):
    x = random.uniform(-30, 30); y = random.uniform(14, 30)
    if abs(x) < 9: y += 6
    h = random.uniform(6, 13)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=h * 0.35, location=(x, y, h * 0.7)); o = bpy.context.object
    o.scale = (1, 1, 1.35); o.data.materials.append(tree)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=h * 0.5, location=(x, y, h * 0.25)); bpy.context.object.data.materials.append(tree)
# palms framing the house
for x in (-9.5, 11):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=8, location=(x, 1.5, 4)); bpy.context.object.data.materials.append(tree)
    for k in range(8):
        a = k / 8 * 6.283
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x + math.cos(a) * 1.4, 1.5 + math.sin(a) * 1.4, 7.8))
        o = bpy.context.object; o.scale = (3.0, 0.35, 0.05); o.rotation_euler = (0, math.radians(18), a); o.data.materials.append(tree)

cam = camera((0, -13, 0.5), (0, 3, 1.6), lens=32, dof=12, fstop=2.8)
key_cam(cam, [
    (1, (-1.6, -9.6, 0.42), (0, 2, 2.6), 12.0),
    (N, (0.2, -4.0, 1.5), (0, 3.4, 1.55), 7.5),
])
for fc in cam.animation_data.action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'
only = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else None
render_range(SP + '/r/home', 1, N, only)
