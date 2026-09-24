import os, sys, bpy, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

random.seed(11)


def tower_mat(name, lit=0.35, warm=(1.0, 0.72, 0.4), glass=(0.02, 0.03, 0.05), wscale=1.0, emit=6.0, cw=3.2, ch=3.8):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    b.inputs['Base Color'].default_value = (*glass, 1)
    b.inputs['Metallic'].default_value = 0.85
    b.inputs['Roughness'].default_value = 0.14
    def M(op, a=None, bb=None, v=None):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op
        if a is not None: L(a, n.inputs[0])
        if bb is not None: L(bb, n.inputs[1])
        if v is not None: n.inputs[1].default_value = v
        return n.outputs[0]
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Object'], sep.inputs[0])
    u = M('ADD', sep.outputs[0], sep.outputs[1]); v = sep.outputs[2]
    us = M('DIVIDE', u, v=cw * wscale); vs = M('DIVIDE', v, v=ch * wscale)
    fu = M('FRACT', us); fv = M('FRACT', vs)
    mu = M('LESS_THAN', fu, v=0.62); mv = M('LESS_THAN', fv, v=0.58)
    win = M('MULTIPLY', mu, mv)
    cu = M('FLOOR', us); cv = M('FLOOR', vs)
    comb = nt.nodes.new('ShaderNodeCombineXYZ'); L(cu, comb.inputs[0]); L(cv, comb.inputs[1])
    oi = nt.nodes.new('ShaderNodeObjectInfo'); L(oi.outputs['Random'], comb.inputs[2])
    wn = nt.nodes.new('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '3D'; L(comb.outputs[0], wn.inputs['Vector'])
    on = M('GREATER_THAN', wn.outputs['Value'], v=1 - lit)
    # whole floors sometimes dark / lit in bands for realism
    band = nt.nodes.new('ShaderNodeTexWhiteNoise'); band.noise_dimensions = '1D'; L(cv, band.inputs['W'])
    bandk = M('GREATER_THAN', band.outputs['Value'], v=0.25)
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sn = nt.nodes.new('ShaderNodeSeparateXYZ'); L(geo.outputs['Normal'], sn.inputs[0])
    side = M('LESS_THAN', M('ABSOLUTE', sn.outputs[2]), v=0.5)
    k = M('MULTIPLY', M('MULTIPLY', M('MULTIPLY', win, on), side), bandk)
    # colour variation per window
    mixc = nt.nodes.new('ShaderNodeMix'); mixc.data_type = 'RGBA'
    L(wn.outputs['Color'], mixc.inputs['Factor']); mixc.inputs['Factor'].hide = False
    mixc.inputs[6].default_value = (*warm, 1); mixc.inputs[7].default_value = (1.0, 0.78, 0.5, 1)
    L(mixc.outputs[2], b.inputs['Emission Color'])
    str_ = M('MULTIPLY', k, v=emit)
    str2 = M('MULTIPLY', str_, M('ADD', wn.outputs['Value'], v=0.3))
    L(str2, b.inputs['Emission Strength'])
    return m


def build_city(hero_h=260, extent=9, seed=11):
    random.seed(seed)
    mats = [tower_mat('tw1', 0.14, (1.0, 0.5, 0.16), emit=1.6), tower_mat('tw2', 0.2, (0.45, 0.62, 1.0), emit=1.3), tower_mat('tw3', 0.12, (1.0, 0.62, 0.28), emit=1.8)]
    block, street = 44, 14
    for i in range(-extent, extent + 1):
        for j in range(-extent, extent + 1):
            cx, cy = i * (block + street), j * (block + street)
            if i == 0 and j == 0:
                continue
            dist = math.hypot(i, j)
            n = random.choice([1, 2, 2, 4])
            sub = block / (2 if n > 1 else 1)
            spots = [(0, 0)] if n == 1 else [(-sub / 2, -sub / 2), (sub / 2, -sub / 2), (-sub / 2, sub / 2), (sub / 2, sub / 2)][:n + (n == 2) * 0]
            for (ox, oy) in spots:
                w = sub * random.uniform(0.6, 0.92)
                d = sub * random.uniform(0.6, 0.92)
                h = random.uniform(20, 70) + max(0, 170 - dist * 18) * random.random() ** 1.5
                if random.random() < 0.06: h *= 1.8
                o = cube((cx + ox, cy + oy, h / 2), (w, d, h), random.choice(mats))
                bpy.ops.object.transform_apply(scale=True)
    # hero tower: stepped glass spire with a lit crown
    hm = tower_mat('hero', 0.3, (1.0, 0.55, 0.2), wscale=0.8, emit=2.2)
    z = 0
    for k, (w, h) in enumerate([(40, hero_h * 0.55), (32, hero_h * 0.3), (24, hero_h * 0.15)]):
        cube((0, 0, z + h / 2), (w, w, h), hm); bpy.ops.object.transform_apply(scale=True); z += h
    crown = emission_mat('crown', (1.0, 0.55, 0.18), 12)
    roof = mat('roof', (0.02, 0.02, 0.025), 0.9, 0.3)
    zz = 0
    for (w, h) in [(40, hero_h * 0.55), (32, hero_h * 0.3), (24, hero_h * 0.15)]:
        zz += h
        cube((0, 0, zz + 0.3), (w - 0.5, w - 0.5, 0.6), roof)
        for sx, sy, lx, ly in [(0, w / 2, w, 0.5), (0, -w / 2, w, 0.5), (w / 2, 0, 0.5, w), (-w / 2, 0, 0.5, w)]:
            cube((sx, sy, zz + 0.4), (lx + 0.3, ly + 0.3, 0.5), crown)
    for k in range(6):
        w = 22 - k * 3.2
        for sx, sy, lx, ly in [(0, w / 2, w, 0.35), (0, -w / 2, w, 0.35), (w / 2, 0, 0.35, w), (-w / 2, 0, 0.35, w)]:
            cube((sx, sy, z + 2 + k * 4), (lx, ly, 0.35), crown)
    bpy.ops.mesh.primitive_cone_add(radius1=3, radius2=0.2, depth=40, location=(0, 0, z + 38))
    bpy.context.object.data.materials.append(mat('spire', (0.6, 0.5, 0.3), 1, 0.2))
    beacon = emission_mat('beacon', (1, 0.2, 0.15), 60)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, location=(0, 0, z + 59)); bpy.context.object.data.materials.append(beacon)
    # ground + street lights
    g = mat('ground', (0.01, 0.01, 0.012), 0.0, 0.25)
    nt = g.node_tree; b = nt.nodes['Principled BSDF']
    vor = nt.nodes.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 0.09
    cr = nt.nodes.new('ShaderNodeMapRange'); cr.inputs[1].default_value = 0.12; cr.inputs[2].default_value = 0.02
    nt.links.new(vor.outputs['Distance'], cr.inputs[0])
    wn = nt.nodes.new('ShaderNodeTexNoise'); wn.inputs['Scale'].default_value = 0.004
    mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = 5
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'
    nt.links.new(cr.outputs[0], m2.inputs[0]); nt.links.new(wn.outputs['Fac'], m2.inputs[1])
    nt.links.new(m2.outputs[0], mm.inputs[0])
    b.inputs['Emission Color'].default_value = (1.0, 0.55, 0.2, 1)
    nt.links.new(mm.outputs[0], b.inputs['Emission Strength'])
    bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, 0)); bpy.context.object.data.materials.append(g)
    sl = emission_mat('street', (1.0, 0.5, 0.18), 8)
    span = extent * (block + street) + block
    for i in range(-extent, extent + 1):
        c = i * (block + street) + (block + street) / 2
        cube((c, 0, 0.1), (1.2, span * 2, 0.2), sl)
        cube((0, c, 0.1), (span * 2, 1.2, 0.2), sl)
    # moving car light streaks on two avenues
    return z


if __name__ == '__main__':
    sc = reset(samples=int(sys.argv[2]) if len(sys.argv) > 2 else 20)
    sc.render.resolution_x, sc.render.resolution_y = 576, 1024
    world_gradient((0.004, 0.012, 0.05), (0.55, 0.22, 0.12), strength=1.0)
    mist_output(SP + '/r/city', 150, 3200)
    top = build_city()
    # soft moonlight/fill
    light('SUN', (0, 0, 100), 0.25, (0.6, 0.7, 1.0), size=3, rot=(math.radians(60), 0, math.radians(30)))
    cam = camera((-18, -48, 6), (0, 0, 40), lens=24)
    cam.data.dof.use_dof = False
    # 84 frames: street level -> race up the facade -> crest the crown -> look out
    key_cam(cam, [
        (1, (-26, -52, 4), (0, 0, 60)),
        (40, (-30, -44, 150), (0, 0, 230)),
        (70, (-44, -64, top + 40), (0, 0, top + 20)),
        (96, (-80, -120, top + 70), (0, 0, top + 10)),
    ])
    for fc in cam.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'
    sc.cycles.samples = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    dump_horizon(SP + '/r/city_horizon.json', 1, 96)
    if sys.argv[1] == 'horizon': sys.exit()
    only = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else None
    render_range(SP + '/r/city', 1, 96, only)
