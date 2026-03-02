"""
Blender mesh creation and extraction for CoH GEO files.

Converts between GEO binary format data classes and Blender mesh objects.
Handles coordinate conversion, UV mapping, material assignment, and
optional bone skinning.

Similar to armature.py but for geometry instead of animations.
"""

try:
    import bpy
    import bmesh
    _HAS_BPY = True
except ImportError:
    _HAS_BPY = False

from .formats.geo import GeoFile, GeoModel, GeoHeader, TexID
from .core.coords import game_to_blender, blender_to_game
import math


# ─── Import: GEO → Blender ──────────────────────────────────────────────


def mesh_from_geo(context, geo_file, name="GEO_Import"):
    """Create Blender mesh objects from a GEO file.

    Args:
        context: Blender context
        geo_file: GeoFile data
        name: Base name for created objects

    Returns:
        List of created Blender objects
    """
    objects = []

    for model in geo_file.models:
        obj = _create_mesh_object(context, model, geo_file.tex_names)
        objects.append(obj)

    return objects


def _create_mesh_object(context, model, tex_names):
    """Create a single Blender mesh object from a GeoModel."""
    mesh = bpy.data.meshes.new(model.name)
    obj = bpy.data.objects.new(model.name, mesh)

    # Convert vertices from game to Blender coordinates
    verts = [game_to_blender(v) for v in model.vertices]
    faces = list(model.triangles)

    mesh.from_pydata(verts, [], faces)
    mesh.update()

    # UV mapping
    if model.uvs:
        uv_layer = mesh.uv_layers.new(name="UVMap")
        for poly in mesh.polygons:
            for li, vi in zip(poly.loop_indices, poly.vertices):
                if vi < len(model.uvs):
                    u, v = model.uvs[vi]
                    # Blender UVs: flip V axis (game uses top-left origin)
                    uv_layer.data[li].uv = (u, 1.0 - v)

    # Secondary UV set
    if model.uvs2:
        uv_layer2 = mesh.uv_layers.new(name="UVMap2")
        for poly in mesh.polygons:
            for li, vi in zip(poly.loop_indices, poly.vertices):
                if vi < len(model.uvs2):
                    u, v = model.uvs2[vi]
                    uv_layer2.data[li].uv = (u, 1.0 - v)

    # Create materials from texture names
    _assign_materials(mesh, model, tex_names)

    # Custom normals
    if model.normals:
        normals = [game_to_blender(n) for n in model.normals]
        # Set normals per-loop
        loop_normals = []
        for poly in mesh.polygons:
            for vi in poly.vertices:
                if vi < len(normals):
                    loop_normals.append(normals[vi])
                else:
                    loop_normals.append((0.0, 0.0, 1.0))
        mesh.normals_split_custom_set(loop_normals)

    # Link to scene
    context.collection.objects.link(obj)

    # Skinning (vertex groups from BoneInfo)
    if model.bone_info and model.bone_info.weights:
        _apply_skinning(obj, model)

    return obj


def _assign_materials(mesh, model, tex_names):
    """Assign materials based on TexID runs."""
    if not model.tex_ids:
        return

    # Create a material for each referenced texture
    mat_indices = {}
    for tex_id_entry in model.tex_ids:
        tid = tex_id_entry.id
        if tid not in mat_indices:
            tex_name = tex_names[tid] if tid < len(tex_names) else f"material_{tid}"
            mat = bpy.data.materials.get(tex_name) or bpy.data.materials.new(tex_name)
            mat_indices[tid] = len(mesh.materials)
            mesh.materials.append(mat)

    # Assign material index to each triangle based on TexID runs
    tri_idx = 0
    for tex_id_entry in model.tex_ids:
        mat_idx = mat_indices.get(tex_id_entry.id, 0)
        for _ in range(tex_id_entry.count):
            if tri_idx < len(mesh.polygons):
                mesh.polygons[tri_idx].material_index = mat_idx
            tri_idx += 1


def _apply_skinning(obj, model):
    """Apply bone skinning data from GeoModel.bone_info to vertex groups."""
    bi = model.bone_info
    if not bi or not bi.matidxs:
        return

    # Create vertex groups for each bone
    bone_groups = {}
    bone_ids = bi.bone_ids if bi.bone_ids else list(range(bi.numbones))

    for bone_id in bone_ids:
        if bone_id not in bone_groups:
            group_name = f"bone_{bone_id}"
            vg = obj.vertex_groups.new(name=group_name)
            bone_groups[bone_id] = vg

    # Assign weights
    for vi in range(model.vert_count):
        if vi >= len(bi.matidxs) or vi >= len(bi.weights):
            continue

        idx0, idx1 = bi.matidxs[vi]
        weight = bi.weights[vi]

        if idx0 < len(bone_ids):
            bid0 = bone_ids[idx0]
            if bid0 in bone_groups:
                bone_groups[bid0].add([vi], weight, 'REPLACE')

        if idx1 < len(bone_ids) and weight < 1.0:
            bid1 = bone_ids[idx1]
            if bid1 in bone_groups:
                bone_groups[bid1].add([vi], 1.0 - weight, 'REPLACE')


# ─── Export: Blender → GEO ──────────────────────────────────────────────


def geo_from_mesh(context, objects, geo_name="custom"):
    """Create a GeoFile from selected Blender mesh objects.

    Args:
        context: Blender context
        objects: List of Blender mesh objects
        geo_name: Name for the GEO file header

    Returns:
        GeoFile ready for writing
    """
    all_tex_names = []
    tex_name_map = {}
    models = []

    for obj in objects:
        if obj.type != 'MESH':
            continue

        model = _extract_mesh(context, obj, all_tex_names, tex_name_map)
        models.append(model)

    obj_names = [m.name for m in models]

    return GeoFile(
        version=8,
        headers=[GeoHeader(name=f"{geo_name}.wrl", model_count=len(models))],
        models=models,
        tex_names=all_tex_names,
        obj_names=obj_names,
    )


def _get_loop_normal_func(mesh):
    """Return a function that reads the loop normal for a given loop index.

    Blender 4.1+ removed calc_normals_split() in favour of corner_normals.
    """
    if hasattr(mesh, 'corner_normals'):
        # Blender 4.1+
        cn = mesh.corner_normals
        def _get(li):
            v = cn[li].vector
            return (v[0], v[1], v[2])
        return _get
    else:
        # Blender 4.0
        mesh.calc_normals_split()
        def _get(li):
            n = mesh.loops[li].normal
            return (n[0], n[1], n[2])
        return _get


def _extract_mesh(context, obj, all_tex_names, tex_name_map):
    """Extract GeoModel data from a Blender mesh object.

    Uses vertex splitting to produce per-vertex normals and UVs compatible
    with the GEO format.  Vertices are duplicated wherever loop normals or
    UVs differ (UV seams, hard edges, etc.) — the same approach 3DS Max
    used when exporting VRML for GetVrml.
    """
    # Get evaluated mesh (apply modifiers)
    depsgraph = context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()

    # Triangulate
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.calc_loop_triangles()

    # Prepare loop-normal reader
    get_loop_normal = _get_loop_normal_func(mesh)

    # UV layers
    uv_layer = mesh.uv_layers[0] if len(mesh.uv_layers) > 0 else None
    uv_layer2 = mesh.uv_layers[1] if len(mesh.uv_layers) > 1 else None

    # ── Vertex splitting ─────────────────────────────────────────────
    # Build unique (position, normal, uv, uv2) vertices from loop data.
    # GEO stores one normal and one UV per vertex, so we duplicate
    # vertices wherever those attributes diverge across face-corners.

    vert_map = {}   # (blender_vi, n_key, uv_key, uv2_key) → new index
    vertices = []
    normals = []
    uvs = []
    uvs2 = []

    # Rounding tolerances — well below GEO quantisation precision
    # (normals: 1/256 ≈ 0.0039, UV1: 1/4096 ≈ 0.00024, UV2: 1/32768)
    def _rn(v):
        return (round(v[0], 4), round(v[1], 4), round(v[2], 4))

    def _ruv(v):
        return (round(v[0], 5), round(v[1], 5))

    def _split_vertex(vi, loop_idx):
        """Return the split-vertex index for this face-corner."""
        n = get_loop_normal(loop_idx)
        n_key = _rn(n)

        if uv_layer:
            raw = uv_layer.data[loop_idx].uv
            uv = (raw[0], 1.0 - raw[1])
            uv_key = _ruv(uv)
        else:
            uv = (0.0, 0.0)
            uv_key = uv

        if uv_layer2:
            raw2 = uv_layer2.data[loop_idx].uv
            uv2 = (raw2[0], 1.0 - raw2[1])
            uv2_key = _ruv(uv2)
        else:
            uv2 = None
            uv2_key = None

        key = (vi, n_key, uv_key, uv2_key)
        idx = vert_map.get(key)
        if idx is not None:
            return idx

        idx = len(vertices)
        vert_map[key] = idx

        co = mesh.vertices[vi].co
        vertices.append(blender_to_game((co.x, co.y, co.z)))
        normals.append(blender_to_game(n))
        uvs.append(uv)
        if uv_layer2:
            uvs2.append(uv2)

        return idx

    # ── Build triangles with split vertices, grouped by material ─────
    mat_groups = {}
    for poly in mesh.polygons:
        mi = poly.material_index
        tri = tuple(
            _split_vertex(vi, li)
            for li, vi in zip(poly.loop_indices, poly.vertices)
        )
        if mi not in mat_groups:
            mat_groups[mi] = []
        mat_groups[mi].append(tri)

    # ── Sorted triangle list and TexID runs ──────────────────────────
    triangles = []
    tex_ids = []

    for mi in sorted(mat_groups.keys()):
        tris = mat_groups[mi]

        if mi < len(mesh.materials) and mesh.materials[mi]:
            tex_name = mesh.materials[mi].name
        else:
            tex_name = "white"

        if tex_name not in tex_name_map:
            tex_name_map[tex_name] = len(all_tex_names)
            all_tex_names.append(tex_name)

        tid = tex_name_map[tex_name]
        tex_ids.append(TexID(id=tid, count=len(tris)))
        triangles.extend(tris)

    # ── Bounding box ─────────────────────────────────────────────────
    if vertices:
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        zs = [v[2] for v in vertices]
        min_bound = (min(xs), min(ys), min(zs))
        max_bound = (max(xs), max(ys), max(zs))
        radius = max(math.sqrt(x*x + y*y + z*z) for x, y, z in vertices)
    else:
        min_bound = (0.0, 0.0, 0.0)
        max_bound = (0.0, 0.0, 0.0)
        radius = 0.0

    model = GeoModel(
        name=f"GEO_{obj.name}",
        radius=radius,
        min=min_bound,
        max=max_bound,
        vert_count=len(vertices),
        tri_count=len(triangles),
        vertices=vertices,
        normals=normals,
        uvs=uvs,
        uvs2=uvs2,
        triangles=triangles,
        tex_ids=tex_ids,
    )

    eval_obj.to_mesh_clear()
    return model
