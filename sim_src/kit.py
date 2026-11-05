"""Blender 메시 도구 + 빛 굽기·내보내기. build_room.py / build_subway.py 가 exec로 불러 씀 (M, TEX, OUT, LM_PX, SAMPLES가 먼저 있어야 함)"""
bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
names = list(M); idx = {n: i for i, n in enumerate(names)}
def face(pts, mat, uvs=None, smooth=False):
    vs = [bm.verts.new(p) for p in pts]; f = bm.faces.new(vs); f.material_index = idx[mat]; f.smooth = smooth
    if uvs is None:
        n = (Vector(pts[1]) - Vector(pts[0])).cross(Vector(pts[2]) - Vector(pts[0]))
        s = M[mat].get('s')
        if s:
            ax = max(range(3), key=lambda i: abs(n[i]))
            uvs = [((p[0] / s[0], p[1] / s[1]) if ax == 2 else (p[0] / s[0], p[2] / s[1]) if ax == 1 else (p[1] / s[0], p[2] / s[1])) for p in pts]
        else:
            uvs = [(0, 0), (1, 0), (1, 1), (0, 1)][:len(pts)] + [(.5, .5)] * max(0, len(pts) - 4)
    for l, uv in zip(f.loops, uvs): l[uvl].uv = uv
    return f
def box(x0, x1, y0, y1, z0, z1, mat, top=None, T=None):
    """축 정렬 상자. top: 윗면만 다른 재질(면에 맞춤). T: 위치 변환 함수"""
    t = T or (lambda p: p)
    P = lambda x, y, z: t((x, y, z))
    a, b, c, d = (x0, y0), (x1, y0), (x1, y1), (x0, y1)
    face([P(*a, z1), P(*b, z1), P(*c, z1), P(*d, z1)], top or mat)
    face([P(*d, z0), P(*c, z0), P(*b, z0), P(*a, z0)], mat)
    for p, q in ((a, b), (b, c), (c, d), (d, a)):
        face([P(*p, z0), P(*q, z0), P(*q, z1), P(*p, z1)], mat)
def sweep(path, r, mat, n=8, T=None, cap=True):
    t = T or (lambda p: p)
    pts = [Vector(p) for p in path]; rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        u = d.cross(Vector((0.3, 0.2, 1))).normalized() if abs(d.z) < .9 else d.cross(Vector((1, 0, 0))).normalized()
        v = d.cross(u); rad = r(i) if callable(r) else r
        rings.append([t(tuple(p + (u * math.cos(k / n * 6.283) + v * math.sin(k / n * 6.283)) * rad)) for k in range(n)])
    vs = [[bm.verts.new(q) for q in ring] for ring in rings]
    for a, b in zip(vs, vs[1:]):
        for k in range(n):
            f = bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k])); f.material_index = idx[mat]; f.smooth = True
    if cap:
        f = bm.faces.new(vs[0][::-1]); f.material_index = idx[mat]; f = bm.faces.new(vs[-1]); f.material_index = idx[mat]
def smooth_path(pts, k=8):
    """Catmull-Rom"""
    P = [Vector(p) for p in pts]; P = [P[0]] + P + [P[-1]]; out = []
    for i in range(1, len(P) - 2):
        a, b, c, d = P[i - 1], P[i], P[i + 1], P[i + 2]
        for j in range(k):
            s = j / k; out.append(.5 * (2 * b + (c - a) * s + (2 * a - 5 * b + 4 * c - d) * s * s + (3 * b - a - 3 * c + d) * s ** 3))
    return out + [P[-2]]
def place(x, y, rot, z=0):
    c, s = math.cos(rot), math.sin(rot)
    return lambda p: (x + p[0] * c - p[1] * s, y + p[0] * s + p[1] * c, z + p[2])


def extrude_x(profile, x0, x1, mat, us=.4, T=None, smooth=True):
    """(y, z) 단면을 x 방향으로 뽑음 + 양끝 막음. 좌석·몰딩용"""
    t = T or (lambda p: p)
    n = len(profile)
    a_ = [bm.verts.new(t((x0, y, z))) for y, z in profile]; b_ = [bm.verts.new(t((x1, y, z))) for y, z in profile]
    run = 0
    for i in range(n):
        j = (i + 1) % n; L = math.dist(profile[i], profile[j])
        f = bm.faces.new((a_[i], b_[i], b_[j], a_[j])); f.material_index = idx[mat]; f.smooth = smooth
        for l, uv in zip(f.loops, ((x0 / us, run / us), (x1 / us, run / us), (x1 / us, (run + L) / us), (x0 / us, (run + L) / us))): l[uvl].uv = uv
        run += L
    for vs in (a_[::-1], b_):
        f = bm.faces.new(vs); f.material_index = idx[mat]
        for l, p in zip(f.loops, (profile[::-1] if vs is not b_ else profile)): l[uvl].uv = (p[0] / us, p[1] / us)

def srgb(h):
    v = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [(c / 12.92 if c < .04045 else ((c + .055) / 1.055) ** 2.4) for c in v] + [1]

def finish(env_loc, sky, extra):
    """메시 완성 → lightmap UV → Cycles 굽기 → env 360° → glb + scene.json"""
    me = bpy.data.meshes.new('room'); bm.normal_update(); bm.to_mesh(me); bm.free()
    obj = bpy.data.objects.new('room', me); bpy.context.collection.objects.link(obj)
    for o in list(bpy.data.objects):
        if o is not obj: bpy.data.objects.remove(o)
    print('tris', sum(len(p.vertices) - 2 for p in me.polygons), 'verts', len(me.vertices), flush=True)
    lm = bpy.data.images.new('lightmap', LM_PX, LM_PX, float_buffer=True, alpha=False)
    imgs = {}
    for n in names:
        d = M[n]; m = bpy.data.materials.new(n); m.use_nodes = True
        nt = m.node_tree; b = nt.nodes['Principled BSDF']
        b.inputs['Roughness'].default_value = d.get('rough', .6); b.inputs['Metallic'].default_value = d.get('metal', 0)
        if 'map' in d:
            tex = nt.nodes.new('ShaderNodeTexImage'); p = f"{TEX}/{d['map']}.jpg"
            tex.image = imgs.setdefault(p, bpy.data.images.load(p))
            uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'; nt.links.new(uvn.outputs[0], tex.inputs['Vector'])
            nt.links.new(tex.outputs['Color'], b.inputs['Base Color'])
            if d.get('emit'):
                nt.links.new(tex.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = d['emit']
        else:
            b.inputs['Base Color'].default_value = srgb(d['color'])
            if d.get('emit'):
                b.inputs['Emission Color'].default_value = srgb(d['color']); b.inputs['Emission Strength'].default_value = d['emit']
        me.materials.append(m)
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = lm; t.name = 'bake'; nt.nodes.active = t
    lmuv = me.uv_layers.new(name='lm')
    bpy.context.view_layer.objects.active = obj; obj.select_set(True)
    me.uv_layers.active = lmuv
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=4 / LM_PX * 1.5, area_weight=0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'; prefs.get_devices()
    for dev in prefs.devices: dev.use = True
    scene.cycles.device = 'GPU'
    scene.cycles.samples = SAMPLES; scene.cycles.max_bounces = 6; scene.cycles.diffuse_bounces = 5
    scene.cycles.glossy_bounces = 2; scene.cycles.use_denoising = False
    scene.cycles.sample_clamp_indirect = 8
    w = bpy.data.worlds.new('sky'); scene.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (.92, .95, 1, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = sky
    scene.render.bake.margin = 6; scene.render.bake.use_pass_color = False
    scene.render.bake.use_pass_direct = True; scene.render.bake.use_pass_indirect = True
    print('baking', flush=True)
    bpy.ops.object.bake(type='DIFFUSE', uv_layer='lm', margin=6, use_clear=True)
    px = np.array(lm.pixels[:], dtype=np.float32).reshape(LM_PX, LM_PX, 4)[::-1, :, :3]
    np.save(f'{OUT}/lightmap.npy', px)
    print('bake done', px.mean(), px.max(), flush=True)
    cam = bpy.data.cameras.new('env'); cam.type = 'PANO'
    cam.panorama_type = 'EQUIRECTANGULAR'
    co = bpy.data.objects.new('env', cam); bpy.context.collection.objects.link(co)
    co.location = env_loc; co.rotation_euler = (math.pi / 2, 0, 0)
    scene.camera = co; scene.render.resolution_x, scene.render.resolution_y = 1024, 512
    scene.cycles.samples = 96; scene.cycles.use_denoising = True
    scene.view_settings.view_transform = 'Standard'; scene.view_settings.look = 'None'; scene.view_settings.exposure = 1.3
    scene.render.image_settings.file_format = 'JPEG'; scene.render.image_settings.quality = 88
    scene.render.filepath = f'{OUT}/env.jpg'
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(co)
    bpy.ops.export_scene.gltf(filepath=f'{OUT}/room.glb', export_format='GLB', use_selection=False, export_image_format='NONE',
        export_materials='EXPORT', export_texcoords=True, export_normals=True, export_apply=False, export_cameras=False, export_lights=False, export_yup=True)
    json.dump({**extra, 'materials': {n: {k: v for k, v in M[n].items() if k in ('color', 'map', 'rough', 'metal', 'emit', 'gain', 'tint', 'unlit')} for n in names}},
              open(f'{OUT}/scene.json', 'w'), ensure_ascii=False)
    print('all done', flush=True)
