import os
import math
import bpy
from . import pcb_parser
from . import footprint_matcher
from . import material_harmony
from . import cleaner

# Cache for library template meshes: {package_name: mesh_data}
_LIBRARY_MESH_CACHE = {}

def get_library_blend_path():
    """Returns absolute path to footprints.blend asset file"""
    core_dir = os.path.dirname(os.path.abspath(__file__))
    addon_dir = os.path.dirname(core_dir)
    return os.path.join(addon_dir, "assets", "footprints.blend")

def get_cached_package_mesh(package_name):
    """
    Retrieves or loads the mesh data for a package from footprints.blend.
    Cached in memory to prevent re-opening the .blend file repeatedly.
    """
    if package_name in _LIBRARY_MESH_CACHE and _LIBRARY_MESH_CACHE[package_name].name in bpy.data.meshes:
        return _LIBRARY_MESH_CACHE[package_name]
        
    blend_path = get_library_blend_path()
    if not os.path.exists(blend_path):
        raise FileNotFoundError(f"Footprints library not found at: {blend_path}")
        
    with bpy.data.libraries.load(blend_path) as (data_from, data_to):
        if package_name in data_from.objects:
            data_to.objects = [package_name]
        else:
            raise ValueError(f"Package '{package_name}' not found in {blend_path}")
            
    loaded_obj = data_to.objects[0]
    mesh = loaded_obj.data
    _LIBRARY_MESH_CACHE[package_name] = mesh
    
    # Don't keep the loaded template object in memory
    bpy.data.objects.remove(loaded_obj, do_unlink=True)
    return mesh

def get_board_transform_context(fps=None):
    """
    Determines the coordinate transformation context:
    - offset_x (in mm)
    - offset_y (in mm)
    - board_thickness (in meters)
    """
    scene = bpy.context.scene
    
    # Check scene stored properties
    if "kicad_board_offset_x" in scene and "kicad_board_offset_y" in scene:
        offset_x = float(scene["kicad_board_offset_x"])
        offset_y = float(scene["kicad_board_offset_y"])
        thickness = float(scene.get("kicad_board_thickness", 0.0016))
        return offset_x, offset_y, thickness
        
    # Deduce from an existing component with kicad_reference in the scene
    if fps:
        for obj in bpy.data.objects:
            ref = obj.get("kicad_reference")
            if ref and ref in fps:
                data = fps[ref]
                offset_x = data["pos_x"] - (obj.location.x * 1000.0)
                offset_y = data["pos_y"] + (obj.location.y * 1000.0)
                sub = bpy.data.objects.get("PCB_Substrate_FR4")
                thickness = sub.dimensions.z if sub else 0.0016
                # Save to scene for future calls
                scene["kicad_board_offset_x"] = offset_x
                scene["kicad_board_offset_y"] = offset_y
                scene["kicad_board_thickness"] = thickness
                return offset_x, offset_y, thickness
                
    # Fallback to PCB_Substrate_FR4 bounds
    sub = bpy.data.objects.get("PCB_Substrate_FR4")
    thickness = sub.dimensions.z if sub else 0.0016
    return 0.0, 0.0, thickness

def scan_missing_components(pcb_path=""):
    """
    Scans the .kicad_pcb file against the current Blender scene.
    Returns:
        dict with total_count, scene_count, missing_count, matched_count, and missing_list
    """
    resolved_pcb = pcb_path.strip() if pcb_path else ""
    if not resolved_pcb:
        resolved_pcb = getattr(bpy.context.scene, 'kicad_custom_pcb_path', '')
        
    if not resolved_pcb or not os.path.exists(resolved_pcb):
        return {
            "error": "No valid .kicad_pcb file specified or found.",
            "missing_list": []
        }
        
    fps = pcb_parser.parse_kicad_pcb(resolved_pcb)
    if not fps:
        return {
            "error": "Could not parse any footprints from the .kicad_pcb file.",
            "missing_list": []
        }
        
    # Gather references of components present in the Blender scene
    scene_refs = set()
    for obj in bpy.data.objects:
        ref = obj.get("kicad_reference")
        if ref:
            scene_refs.add(ref)
            
    missing_list = []
    for ref, data in fps.items():
        if ref not in scene_refs:
            # Match footprint to library package
            pkg, conf = footprint_matcher.match_footprint(ref, data['fp_name'], data['val'])
            missing_list.append({
                "ref": ref,
                "val": data['val'],
                "fp_name": data['fp_name'],
                "layer": data.get('layer', 'F.Cu'),
                "pos_x": data['pos_x'],
                "pos_y": data['pos_y'],
                "rot_z": data['rot_z'],
                "suggested_package": pkg,
                "confidence": conf
            })
            
    # Sort missing list: auto-matched first, then by ref
    missing_list.sort(key=lambda x: (x["suggested_package"] is None, x["ref"]))
    
    matched_count = sum(1 for m in missing_list if m["suggested_package"])
    
    return {
        "status": "success",
        "pcb_file": resolved_pcb,
        "total_footprints": len(fps),
        "scene_components": len(scene_refs),
        "missing_count": len(missing_list),
        "matched_count": matched_count,
        "missing_list": missing_list
    }

def place_component(comp_data, package_name=None, fps=None, scene_mats=None):
    """
    Instantiates a library component, computes exact PCB world coordinates,
    applies material harmony with scene, and categorizes into collections.
    comp_data: dict with ref, val, fp_name, layer, pos_x, pos_y, rot_z
    package_name: optional override for package name (e.g. 'SOIC-8', 'R_0603')
    scene_mats: optional precomputed material palette (see detect_scene_component_materials).
        Pass this when placing a batch to avoid rescanning the scene per component.
    """
    pkg = package_name or comp_data.get("suggested_package")
    if not pkg:
        raise ValueError(f"No package specified for component {comp_data.get('ref')}")
        
    ref = comp_data["ref"]
    val = comp_data.get("val", "")
    
    # 1. Get mesh from library cache
    template_mesh = get_cached_package_mesh(pkg)
    new_mesh = template_mesh.copy()
    new_mesh.name = f"{ref}_{val}_Mesh" if val else f"{ref}_{pkg}_Mesh"
    
    obj_name = f"{ref}_{val}" if val else f"{ref}_{pkg}"
    obj = bpy.data.objects.new(obj_name, new_mesh)
    
    # 2. Add copy of modifiers (e.g. Bevel)
    bev = obj.modifiers.new("Bevel", type='BEVEL')
    bev.width = 0.00008
    bev.segments = 2
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(45)
    
    # 3. Apply harmonized materials to match scene shaders
    material_harmony.apply_harmonized_materials(obj, pkg, scene_mats=scene_mats)
    
    # 4. Compute 3D coordinates based on KiCad position and board offsets
    offset_x, offset_y, board_thickness = get_board_transform_context(fps)
    
    loc_x = (comp_data["pos_x"] - offset_x) * 0.001
    loc_y = -(comp_data["pos_y"] - offset_y) * 0.001
    
    layer = comp_data.get("layer", "F.Cu")
    is_bottom = (layer == "B.Cu")
    
    rot_z_deg = comp_data.get("rot_z", 0.0)
    
    # Board coordinate frame after import: substrate spans z = 0 (bottom face) to
    # +board_thickness (top face). Library meshes are authored with their origin on
    # the seating plane (z=0 of the mesh) and the body extending +Z, so:
    #   - Top side:    origin on the board top face, body grows upward.
    #   - Bottom side: rot_x=pi mirrors the body to -Z, so a slightly negative origin
    #     makes it hang below the board's bottom face.
    if not is_bottom:
        # Top side (F.Cu): Z = top surface + tiny micron offset
        loc_z = board_thickness + 0.00002
        if pkg == "POT_PTV09A":
            loc_z = board_thickness + 0.000302
        rot_x = 0.0
        rot_y = 0.0
        rot_z = math.radians(rot_z_deg)
    else:
        # Bottom side (B.Cu): origin just below the board's bottom face, flipped 180 deg
        loc_z = -0.00002
        rot_x = math.pi
        rot_y = 0.0
        rot_z = math.radians(-rot_z_deg)
        
    obj.location = (loc_x, loc_y, loc_z)
    obj.rotation_euler = (rot_x, rot_y, rot_z)
    
    # 5. Tag metadata
    obj["kicad_reference"] = ref
    obj["kicad_value"] = val
    obj["kicad_footprint"] = comp_data.get("fp_name", "")
    obj["kicad_layer"] = layer
    obj["kicad_placed_by_library"] = True
    obj["kicad_package"] = pkg
    
    # 6. Link to category collection in 05_Components
    comp_parent_col = bpy.data.collections.get("05_Components")
    if comp_parent_col:
        cat_name = cleaner.get_component_category(ref)
        cat_col = bpy.data.collections.get(cat_name)
        if not cat_col:
            cat_col = bpy.data.collections.new(cat_name)
            comp_parent_col.children.link(cat_col)
        cat_col.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)
        
    return obj

def fill_all_matched_components(pcb_path=""):
    """
    Scans for missing components and places all auto-matched packages.
    Returns:
        (placed_count, list_of_placed_objects)
    """
    scan_res = scan_missing_components(pcb_path)
    if "error" in scan_res:
        raise RuntimeError(scan_res["error"])
        
    missing_list = scan_res.get("missing_list", [])
    placed = []
    
    fps = None
    if scan_res.get("pcb_file"):
        fps = pcb_parser.parse_kicad_pcb(scan_res["pcb_file"])

    # Sample the scene material palette ONCE for the whole batch. Previously this ran
    # per component, rescanning every object and material node for each part placed
    # (O(placed * scene_objects)). The scene palette cannot meaningfully change while
    # we only add objects, so one sample is equivalent.
    scene_mats = material_harmony.detect_scene_component_materials()

    for item in missing_list:
        pkg = item.get("suggested_package")
        if pkg:
            try:
                obj = place_component(item, package_name=pkg, fps=fps, scene_mats=scene_mats)
                placed.append(obj)
            except Exception as e:
                print(f"Failed to place {item.get('ref')}: {e}")

    return len(placed), placed
