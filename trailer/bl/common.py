import bpy, math, random, os
from mathutils import Vector, Euler

SP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = SP + '/fonts/'


def reset(samples=16, res=(720, 1280), mblur=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.05
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 4
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 4
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 1.0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.fps = 24
    sc.render.use_motion_blur = mblur
    sc.render.motion_blur_shutter = 0.5
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Punchy'
    sc.render.film_transparent = False
    return sc


def world_color(col, strength=1.0):
    w = bpy.data.worlds.new('W'); bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*col, 1); bg.inputs[1].default_value = strength
    return w


def world_sky(sun_elev_deg, sun_rot_deg=0, strength=1.0, air=1.0, dust=1.0):
    w = bpy.data.worlds.new('W'); bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'NISHITA'
    sky.sun_elevation = math.radians(sun_elev_deg)
    sky.sun_rotation = math.radians(sun_rot_deg)
    sky.air_density = air; sky.dust_density = dust
    sky.sun_disc = True
    nt.links.new(sky.outputs[0], nt.nodes['Background'].inputs[0])
    nt.nodes['Background'].inputs[1].default_value = strength
    return w


def mat(name, base=(0.8, 0.8, 0.8), metal=0.0, rough=0.5, emit=None, emit_str=0.0, alpha=1.0, trans=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*base, 1)
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough
    b.inputs['Alpha'].default_value = alpha
    b.inputs['Transmission Weight'].default_value = trans
    b.inputs['Coat Weight'].default_value = coat
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = emit_str
    return m


def emission_mat(name, col, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission'); o = nt.nodes.new('ShaderNodeOutputMaterial')
    e.inputs[0].default_value = (*col, 1); e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def cube(loc, scale, m=None, name='c'):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.scale = scale; o.name = name
    if m: o.data.materials.append(m)
    return o


def camera(loc, look, lens=35, dof=None, fstop=2.8):
    cd = bpy.data.cameras.new('Cam'); cd.lens = lens; cd.clip_end = 30000; cd.clip_start = 0.05
    cd.sensor_width = 36
    cam = bpy.data.objects.new('Cam', cd); bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.location = loc
    aim(cam, look)
    if dof is not None:
        cd.dof.use_dof = True; cd.dof.focus_distance = dof; cd.dof.aperture_fstop = fstop
    return cam


def aim(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def key_cam(cam, frames):
    """frames: list of (frame, loc, look, [focus]) — keyframed with smooth bezier"""
    for f in frames:
        fr, loc, look = f[:3]
        cam.location = loc; aim(cam, look)
        cam.keyframe_insert('location', frame=fr); cam.keyframe_insert('rotation_euler', frame=fr)
        if len(f) > 3:
            cam.data.dof.focus_distance = f[3]; cam.data.dof.keyframe_insert('focus_distance', frame=fr)
        if len(f) > 4:
            cam.data.lens = f[4]; cam.data.keyframe_insert('lens', frame=fr)


def light(kind, loc, energy, col=(1, 1, 1), size=1.0, rot=None, target=None, spot=45):
    ld = bpy.data.lights.new('L', kind); ld.energy = energy; ld.color = col
    if kind in ('AREA',): ld.size = size
    if kind in ('POINT', 'SPOT'): ld.shadow_soft_size = size
    if kind == 'SPOT': ld.spot_size = math.radians(spot); ld.spot_blend = 0.6
    if kind == 'SUN': ld.angle = math.radians(size)
    o = bpy.data.objects.new('L', ld); bpy.context.collection.objects.link(o)
    o.location = loc
    if target: aim(o, target)
    if rot: o.rotation_euler = rot
    return o


def image_plane(path, loc, height, seq_len=None, start=1, offset=0, emit=1.0, name='card', shadeless=True):
    """Alpha image (or image sequence) card, faces -Y (towards a camera looking +Y)."""
    img = bpy.data.images.load(path)
    w, h = img.size
    if seq_len: img.source = 'SEQUENCE'
    asp = w / h
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=(math.radians(90), 0, 0))
    o = bpy.context.object; o.name = name
    o.scale = (height * asp, height, 1)
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img
    tex.interpolation = 'Cubic'
    if seq_len:
        tex.image_user.frame_duration = seq_len
        tex.image_user.frame_start = start
        tex.image_user.frame_offset = offset
        tex.image_user.use_auto_refresh = True
        tex.image_user.use_cyclic = True
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    mix = nt.nodes.new('ShaderNodeMixShader')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    if shadeless:
        sh = nt.nodes.new('ShaderNodeEmission'); sh.inputs[1].default_value = emit
    else:
        sh = nt.nodes.new('ShaderNodeBsdfPrincipled'); sh.inputs['Roughness'].default_value = 0.6
    nt.links.new(tex.outputs['Color'], sh.inputs[0])
    nt.links.new(tex.outputs['Alpha'], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(sh.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    o.data.materials.append(m)
    # cards shouldn't cast shadows / show in reflections too strongly
    o.visible_shadow = False
    return o, tex


def text3d(body, loc, size, m, font='SourceSansPro-Black.ttf', extrude=0.05, bevel=0.01, align='CENTER', rot=(math.radians(90), 0, 0)):
    cu = bpy.data.curves.new('T', 'FONT'); cu.body = body
    cu.font = bpy.data.fonts.load(FONT_DIR + font) if font.startswith('Source') else bpy.data.fonts.load(font)
    cu.size = size; cu.extrude = extrude; cu.bevel_depth = bevel; cu.bevel_resolution = 2
    cu.align_x = align; cu.align_y = 'CENTER'
    o = bpy.data.objects.new('T', cu); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    o.data.materials.append(m)
    return o


def render_range(outdir, f0, f1, only=None):
    sc = bpy.context.scene
    os.makedirs(outdir, exist_ok=True)
    sc.frame_start, sc.frame_end = f0, f1
    frames = only if only else range(f0, f1 + 1)
    for f in frames:
        p = f'{outdir}/{f:04d}.png'
        if os.path.exists(p) and not only: continue
        sc.frame_set(f)
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)


def world_gradient(top, horizon, below=(0.01, 0.01, 0.015), strength=1.0, sharp=3.0):
    """cheap dusk sky: gradient on view direction z"""
    w = bpy.data.worlds.new('W'); bpy.context.scene.world = w
    w.use_nodes = True; nt = w.node_tree
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    mp = nt.nodes.new('ShaderNodeMapRange')
    mp.inputs[1].default_value = -0.02; mp.inputs[2].default_value = 0.45
    nt.links.new(sep.outputs[2], mp.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = (*horizon, 1)
    ramp.color_ramp.elements[1].position = 1.0; ramp.color_ramp.elements[1].color = (*top, 1)
    e = ramp.color_ramp.elements.new(0.25); e.color = tuple(h * 0.5 + t * 0.5 for h, t in zip(horizon, top)) + (1,)
    nt.links.new(mp.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], nt.nodes['Background'].inputs[0])
    nt.nodes['Background'].inputs[1].default_value = strength
    return w


def add_fog(col, start, depth, amount=1.0, falloff='QUADRATIC'):
    sc = bpy.context.scene
    sc.view_layers[0].use_pass_mist = True
    sc.world.mist_settings.start = start; sc.world.mist_settings.depth = depth
    sc.world.mist_settings.falloff = falloff
    sc.use_nodes = True
    nt = sc.node_tree
    rl = nt.nodes.get('Render Layers') or nt.nodes.new('CompositorNodeRLayers')
    comp = nt.nodes.get('Composite') or nt.nodes.new('CompositorNodeComposite')
    mul = nt.nodes.new('CompositorNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = amount
    nt.links.new(rl.outputs['Mist'], mul.inputs[0])
    sa = nt.nodes.new('CompositorNodeSetAlpha'); sa.mode = 'REPLACE_ALPHA'
    mix = nt.nodes.new('CompositorNodeMixRGB')
    mix.inputs[2].default_value = (*col, 1)
    nt.links.new(mul.outputs[0], mix.inputs[0]); nt.links.new(rl.outputs['Image'], mix.inputs[1])
    nt.links.new(mix.outputs[0], sa.inputs[0]); nt.links.new(rl.outputs['Alpha'], sa.inputs[1])
    nt.links.new(sa.outputs[0], comp.inputs[0])


def mist_output(outdir, start, depth, falloff='QUADRATIC'):
    """transparent film + separate mist pass file; fog & sky are composited later in numpy"""
    sc = bpy.context.scene
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = 'RGBA'
    sc.view_layers[0].use_pass_mist = True
    sc.world.mist_settings.start = start; sc.world.mist_settings.depth = depth
    sc.world.mist_settings.falloff = falloff
    sc.use_nodes = True
    nt = sc.node_tree
    rl = nt.nodes.get('Render Layers') or nt.nodes.new('CompositorNodeRLayers')
    comp = nt.nodes.get('Composite') or nt.nodes.new('CompositorNodeComposite')
    nt.links.new(rl.outputs['Image'], comp.inputs[0])
    fo = nt.nodes.new('CompositorNodeOutputFile')
    fo.base_path = outdir + '/mist'
    fo.format.file_format = 'PNG'; fo.format.color_mode = 'BW'; fo.format.color_depth = '16'
    fo.file_slots[0].path = 'm'
    nt.links.new(rl.outputs['Mist'], fo.inputs[0])


def dump_horizon(path, f0, f1):
    import json
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene; cam = sc.camera; out = {}
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        fwd = cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))
        fwd.z = 0
        if fwd.length < 1e-6: fwd = Vector((0, 1, 0))
        fwd.normalize()
        p = cam.matrix_world.translation + fwd * 1e6
        p.z = cam.matrix_world.translation.z
        v = world_to_camera_view(sc, cam, p)
        out[f] = 1 - v.y  # 0 = top of frame, 1 = bottom
    json.dump(out, open(path, 'w'))
