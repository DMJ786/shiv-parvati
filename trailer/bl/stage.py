import os, sys, bpy, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

random.seed(8)
N = 84
sc = reset(samples=int(sys.argv[2]) if len(sys.argv) > 2 else 14)
sc.render.resolution_x, sc.render.resolution_y = 576, 1024
world_color((0.0, 0.0, 0.0), 0)

# floors
black_gloss = mat('bg', (0.004, 0.004, 0.005), 0.0, 0.3, coat=0.3)
cube((0, 7, 0.5), (26, 14, 1.0), black_gloss)            # stage block, front edge at y=0
cube((0, -10, -0.01), (40, 20, 0.02), mat('hall', (0.01, 0.01, 0.01), 0, 0.6))
edge = emission_mat('edge', (1.0, 0.6, 0.25), 6)
cube((0, 0.0, 1.0), (22, 0.04, 0.03), edge)              # glowing stage lip

# LED wall showing him (IMAG) + frame
led, tex = image_plane(SP + '/led/0001.png', (0, 11, 5.6), 4.6, seq_len=N, emit=0.8, name='led')
cube((0, 11.06, 5.6), (8.5, 0.05, 4.9), mat('frame', (0.005, 0.005, 0.005), 0.5, 0.4))

# speaker card behind podium
card, ctex = image_plane(SP + '/seq_stage/0001.png', (0, 2.6, 2.5), 0.82, seq_len=N, emit=1.0, name='him')
pod = mat('pod', (0.02, 0.02, 0.025), 0.6, 0.25)
cube((0, 2.25, 1.0 + 0.52), (0.66, 0.42, 1.04), pod)
cube((0, 2.03, 1.85), (0.46, 0.01, 0.022), emission_mat('podgold', (1.0, 0.7, 0.3), 8))
cube((0, 2.05, 2.05), (0.7, 0.48, 0.03), mat('podtop', (0.6, 0.45, 0.2), 1.0, 0.3))

# truss + beams
truss_l = emission_mat('bulb', (1.0, 0.85, 0.6), 30)
beam_cols = [(1.0, 0.8, 0.5), (0.5, 0.65, 1.0), (1.0, 0.8, 0.5), (0.5, 0.65, 1.0), (1.0, 0.8, 0.5), (0.6, 0.7, 1.0)]
beams = []
for i, x in enumerate([-7, -4.2, -1.4, 1.4, 4.2, 7]):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(x, 1.5, 9.5)); bpy.context.object.data.materials.append(truss_l)
    m = bpy.data.materials.new(f'beam{i}'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    ad = nt.nodes.new('ShaderNodeAddShader'); lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs[0].default_value = 0.5
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs['Facing'], inv.inputs[1])
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 3
    nt.links.new(inv.outputs[0], pw.inputs[0])
    # fade along the beam (object z: top=+depth/2)
    tc = nt.nodes.new('ShaderNodeTexCoord'); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sp.inputs[0])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
    nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(sp.outputs[2], mul.inputs[1])
    mul2 = nt.nodes.new('ShaderNodeMath'); mul2.operation = 'MULTIPLY'; mul2.inputs[1].default_value = 0.7
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    em.inputs[0].default_value = (*beam_cols[i], 1); nt.links.new(mul2.outputs[0], em.inputs[1])
    nt.links.new(em.outputs[0], ad.inputs[0]); nt.links.new(tr.outputs[0], ad.inputs[1]); nt.links.new(ad.outputs[0], o.inputs[0])
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.9, radius2=0.08, depth=10, end_fill_type='NOTHING', location=(0, 0, -5))
    cone = bpy.context.object; cone.data.materials.append(m)
    cone.visible_shadow = False
    piv = bpy.data.objects.new('piv', None); bpy.context.collection.objects.link(piv)
    piv.location = (x, 3.5, 9.5); cone.parent = piv
    ph = random.uniform(0, 6)
    for f in range(1, N + 1, 12):
        piv.rotation_euler = (math.radians(-12 + 10 * math.sin(f / 20 + ph)), math.radians(-x * 3 + 12 * math.sin(f / 16 + ph * 2)), 0)
        piv.keyframe_insert('rotation_euler', frame=f)
    beams.append(piv)

# audience silhouettes
dark = mat('crowd', (0.012, 0.012, 0.014), 0.0, 0.7)
phone = emission_mat('phone', (0.85, 0.9, 1.0), 4)
for row in range(12):
    yy = -2.2 - row * 0.95
    for k in range(18):
        xx = -8 + k * 0.95 + random.uniform(-0.25, 0.25) + (row % 2) * 0.45
        hz = 1.62 + random.uniform(-0.1, 0.12)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.105, location=(xx, yy, hz), segments=16, ring_count=8)
        bpy.context.object.data.materials.append(dark); bpy.context.object.scale = (1, 1.1, 1.18)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25, location=(xx, yy, hz - 0.33), segments=16, ring_count=8)
        bpy.context.object.data.materials.append(dark); bpy.context.object.scale = (0.95, 0.55, 0.45)
        if random.random() < 0.12:
            cube((xx + 0.12, yy + 0.05, hz + 0.3), (0.07, 0.01, 0.13), phone)

# key light on podium area + back fill
light('SPOT', (0, -4, 6), 900, (1.0, 0.85, 0.7), size=0.4, target=(0, 2.4, 2.0), spot=25)
light('AREA', (0, 6, 3), 120, (0.4, 0.55, 1.0), size=6, target=(0, 0, 1.5))

cam = camera((0, -9, 1.75), (0, 2.6, 2.35), lens=50, dof=11.1, fstop=1.8)
key_cam(cam, [
    (1, (-0.5, -8.8, 2.15), (0, 2.6, 2.85), 11.4),
    (N, (0.3, -5.6, 2.3), (0, 2.6, 2.55), 8.2),
])
for fc in cam.animation_data.action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'

mist_output(SP + '/r/stage', 3, 26, 'LINEAR')
only = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else None
render_range(SP + '/r/stage', 1, N, only)
