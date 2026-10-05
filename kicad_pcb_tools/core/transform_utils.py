import bpy
import math
import mathutils
from . import pcb_parser

def look_at(obj, target):
    """Rotates an object so its -Z axis points towards target with Y as up"""
    direction = target - obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    obj.rotation_euler = rot_quat.to_euler()

def center_and_orient_board(pcb_new_objects=None, scale_to_meters=True, board_objects=None, pcb_filepath=None):
    """
    1. Rotates ONLY imported PCB objects -90 degrees around X to lay the PCB flat on the XY plane.
    2. Centers the board bounding box at (0, 0, 0) with bottom at Z=0.
    3. Scales ONLY imported PCB objects from VRML millimeters to Blender meters (factor 0.001).
    4. Sets origin of board layer meshes to the board center (0, 0, 0) while preserving component footprint origins.
    Existing user objects in the scene outside the PCB are never modified!
    """
    if pcb_new_objects is not None:
        # Guard against freed objects. Using a name set is O(1) per object,
        # whereas `o in bpy.data.objects.values()` rebuilds a full list every
        # iteration (O(n^2) on large imports).
        live_names = set(bpy.data.objects.keys())
        target_objs = [o for o in pcb_new_objects if o.name in live_names]
    else:
        # Fallback to KiCad_PCB collection
        pcb_col = bpy.data.collections.get("KiCad_PCB")
        if pcb_col:
            target_objs = [o for o in pcb_col.all_objects]
        else:
            target_objs = [o for o in bpy.data.objects if o.name.startswith(("PCB_", "SHAPE_", "Component_"))]
            
    mesh_objs = [o for o in target_objs if o.type == 'MESH']
    if not mesh_objs:
        return
        
    # Rotate imported PCB objects flat (-90 deg X)
    rot_matrix = mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'X')
    for obj in target_objs:
        if obj.type in ['MESH', 'EMPTY']:
            obj.matrix_world = rot_matrix @ obj.matrix_world
            
    # Apply rotation only to target PCB mesh objects
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs:
        obj.select_set(True)
    if mesh_objs:
        bpy.context.view_layer.objects.active = mesh_objs[0]
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    bpy.ops.object.select_all(action='DESELECT')

    # Calculate bounding box of target PCB objects (in mm)
    min_coord = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    max_coord = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
    
    for obj in mesh_objs:
        for corner in [obj.matrix_world @ mathutils.Vector(b) for b in obj.bound_box]:
            min_coord.x = min(min_coord.x, corner.x)
            min_coord.y = min(min_coord.y, corner.y)
            min_coord.z = min(min_coord.z, corner.z)
            max_coord.x = max(max_coord.x, corner.x)
            max_coord.y = max(max_coord.y, corner.y)
            max_coord.z = max(max_coord.z, corner.z)
            
    # Calculate board center based on substrate FR4 if present, else all mesh objects
    sub = bpy.data.objects.get("PCB_Substrate_FR4")
    if sub and sub in mesh_objs:
        corners = [sub.matrix_world @ mathutils.Vector(b) for b in sub.bound_box]
        min_x = min(c.x for c in corners)
        max_x = max(c.x for c in corners)
        min_y = min(c.y for c in corners)
        max_y = max(c.y for c in corners)
        min_z = min(c.z for c in corners)
        max_z = max(c.z for c in corners)
        center_offset = mathutils.Vector((
            (min_x + max_x) / 2.0,
            (min_y + max_y) / 2.0,
            min_z  # bottom of substrate at Z=0
        ))
    else:
        center_offset = mathutils.Vector((
            (min_coord.x + max_coord.x) / 2.0,
            (min_coord.y + max_coord.y) / 2.0,
            min_coord.z  # bottom of board at Z=0
        ))
    
    # Store board offsets for library component placer
    scene = bpy.context.scene
    scene["kicad_board_offset_x"] = float(center_offset.x)
    scene["kicad_board_offset_y"] = float(-center_offset.y)
    if sub and sub in mesh_objs:
        scene["kicad_board_thickness"] = float(max_z - min_z) * 0.001
    else:
        scene["kicad_board_thickness"] = 0.0016

    # Record the true board outline (Edge.Cuts) for downstream checks. The centering
    # above deliberately still uses the substrate bounding box: it is robust to boards
    # whose Edge.Cuts are arcs/curves, whereas the outline is reported information.
    if pcb_filepath:
        try:
            outline = pcb_parser.get_board_outline_bounds(pcb_filepath)
        except Exception as e:
            print(f"[KiCad PCB Tools] Warning: Failed to parse board outline bounds from {pcb_filepath}: {e}")
            outline = None
        if outline:
            scene["kicad_outline_width_mm"] = float(outline["width"])
            scene["kicad_outline_height_mm"] = float(outline["height"])
            scene["kicad_outline_source"] = "Edge.Cuts"
        
    # Translate only target PCB objects so board center is at (0, 0, 0)
    for obj in target_objs:
        if obj.type in ['MESH', 'EMPTY']:
            obj.location -= center_offset

    # Scale from mm to real-world meters (0.001) ONLY for imported PCB objects
    if scale_to_meters:
        for obj in target_objs:
            if obj.type in ['MESH', 'EMPTY']:
                obj.location *= 0.001
                obj.scale *= 0.001

        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objs:
            obj.select_set(True)
        if mesh_objs:
            bpy.context.view_layer.objects.active = mesh_objs[0]
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bpy.ops.object.select_all(action='DESELECT')

    # Apply location ONLY to board layer meshes so their origins are exactly at the board center (0, 0, 0).
    # Components retain their individual centers at their own footprint coordinates.
    if board_objects:
        live_names = set(bpy.data.objects.keys())
        board_mesh_objs = [o for o in board_objects if o.name in live_names and o.type == 'MESH']
    else:
        board_mesh_objs = [
            o for o in mesh_objs 
            if o.name.startswith("PCB_") or o.name.startswith("Shape_IndexedFaceSet")
        ]

    if board_mesh_objs:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in board_mesh_objs:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = board_mesh_objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        bpy.ops.object.select_all(action='DESELECT')

def recenter_board_to_origin(pcb_objects=None):
    """
    Recenters an already imported, flat, and real-scale PCB to the world origin (0, 0, 0).
    NEVER re-rotates and NEVER re-scales the board (completely prevents board shrinking)!
    """
    if pcb_objects is not None:
        live_names = set(bpy.data.objects.keys())
        target_objs = [o for o in pcb_objects if o.name in live_names]
    else:
        pcb_col = bpy.data.collections.get("KiCad_PCB")
        if pcb_col:
            target_objs = [o for o in pcb_col.all_objects]
        else:
            target_objs = [o for o in bpy.data.objects if o.name.startswith(("PCB_", "SHAPE_", "Component_"))]
            
    mesh_objs = [o for o in target_objs if o.type == 'MESH']
    if not mesh_objs:
        return
        
    sub = bpy.data.objects.get("PCB_Substrate_FR4")
    if sub and sub in mesh_objs:
        corners = [sub.matrix_world @ mathutils.Vector(b) for b in sub.bound_box]
        min_x = min(c.x for c in corners)
        max_x = max(c.x for c in corners)
        min_y = min(c.y for c in corners)
        max_y = max(c.y for c in corners)
        min_z = min(c.z for c in corners)
        center_offset = mathutils.Vector((
            (min_x + max_x) / 2.0,
            (min_y + max_y) / 2.0,
            min_z  # bottom of substrate at Z=0
        ))
    else:
        min_coord = mathutils.Vector((float('inf'), float('inf'), float('inf')))
        max_coord = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
        for obj in mesh_objs:
            for corner in [obj.matrix_world @ mathutils.Vector(b) for b in obj.bound_box]:
                min_coord.x = min(min_coord.x, corner.x)
                min_coord.y = min(min_coord.y, corner.y)
                min_coord.z = min(min_coord.z, corner.z)
                max_coord.x = max(max_coord.x, corner.x)
                max_coord.y = max(max_coord.y, corner.y)
                max_coord.z = max(max_coord.z, corner.z)
        center_offset = mathutils.Vector((
            (min_coord.x + max_coord.x) / 2.0,
            (min_coord.y + max_coord.y) / 2.0,
            min_coord.z
        ))
        
    # Translate target PCB objects so board center is at (0, 0, 0)
    for obj in target_objs:
        if obj.type in ['MESH', 'EMPTY']:
            obj.location -= center_offset
            
    # Apply location ONLY to board layer meshes so their origins remain at (0, 0, 0)
    board_mesh_objs = [o for o in mesh_objs if o.name.startswith("PCB_")]
    if board_mesh_objs:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in board_mesh_objs:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = board_mesh_objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        bpy.ops.object.select_all(action='DESELECT')

def setup_studio_lighting_and_camera():
    """
    Creates high-end 3-point soft studio lighting, an ambient world environment,
    and an auto-framed hero camera targeting the real-scale PCB center.
    """
    scene = bpy.context.scene
    
    # Ensure World exists with soft neutral studio ambient illumination
    if not scene.world:
        scene.world = bpy.data.worlds.new("KiCad_Studio_World")
    world = scene.world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs['Color'].default_value = (0.18, 0.20, 0.22, 1.0)
        bg_node.inputs['Strength'].default_value = 0.8
        
    # Collection for Studio
    studio_col = bpy.data.collections.get("Studio_Lighting_and_Cam")
    if not studio_col:
        studio_col = bpy.data.collections.new("Studio_Lighting_and_Cam")
        scene.collection.children.link(studio_col)
    else:
        # Clear existing studio objects
        for o in list(studio_col.objects):
            bpy.data.objects.remove(o, do_unlink=True)
            
    # Calculate PCB bounding dimensions in meters
    sub = bpy.data.objects.get("PCB_Substrate_FR4")
    dim_x = sub.dimensions.x if sub else 0.15
    dim_y = sub.dimensions.y if sub else 0.10
    max_dim = max(dim_x, dim_y, 0.05)
    
    # 1. Key Light (Soft Warm Area Light)
    key_data = bpy.data.lights.new(name="Studio_Key_Light", type='AREA')
    key_data.energy = 2.0 * (max_dim / 0.15) ** 2
    key_data.color = (1.0, 0.97, 0.93)
    key_data.size = max_dim * 2.0
    key_data.shape = 'RECTANGLE'
    key_data.size_y = max_dim * 1.5
    key_obj = bpy.data.objects.new("Studio_Key_Light", key_data)
    key_obj.location = (max_dim * 1.0, -max_dim * 1.0, max_dim * 1.4)
    look_at(key_obj, mathutils.Vector((0, 0, 0)))
    studio_col.objects.link(key_obj)
    
    # 2. Fill Light (Soft Cool Area Light)
    fill_data = bpy.data.lights.new(name="Studio_Fill_Light", type='AREA')
    fill_data.energy = 1.0 * (max_dim / 0.15) ** 2
    fill_data.color = (0.90, 0.94, 1.0)
    fill_data.size = max_dim * 2.5
    fill_obj = bpy.data.objects.new("Studio_Fill_Light", fill_data)
    fill_obj.location = (-max_dim * 1.2, -max_dim * 0.8, max_dim * 1.2)
    look_at(fill_obj, mathutils.Vector((0, 0, 0)))
    studio_col.objects.link(fill_obj)
    
    # 3. Rim Light (Backlight for edge separation)
    rim_data = bpy.data.lights.new(name="Studio_Rim_Light", type='AREA')
    rim_data.energy = 1.5 * (max_dim / 0.15) ** 2
    rim_data.color = (1.0, 1.0, 1.0)
    rim_data.size = max_dim * 1.5
    rim_obj = bpy.data.objects.new("Studio_Rim_Light", rim_data)
    rim_obj.location = (0.0, max_dim * 1.4, max_dim * 1.2)
    look_at(rim_obj, mathutils.Vector((0, 0, 0)))
    studio_col.objects.link(rim_obj)
    
    # 4. Hero Camera
    cam_data = bpy.data.cameras.new(name="PCB_Hero_Camera")
    cam_data.lens = 85.0  # Portrait telephoto for zero distortion
    cam_data.clip_start = 0.005
    cam_data.clip_end = 100.0
    
    cam_obj = bpy.data.objects.new("PCB_Hero_Camera", cam_data)
    cam_dist = max_dim * 2.6
    cam_obj.location = (0.0, -cam_dist * 0.85, cam_dist * 0.85)
    look_at(cam_obj, mathutils.Vector((0, 0, 0)))
    studio_col.objects.link(cam_obj)
    
    scene.camera = cam_obj

