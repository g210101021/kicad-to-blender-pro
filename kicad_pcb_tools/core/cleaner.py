import os
import re
import bpy
import mathutils
from . import material_engine
from . import pcb_parser

def _material_signature(mat):
    """
    Build a comparable fingerprint of a material's shading so two materials can be
    judged visually identical. Name is deliberately NOT part of the signature.

    Compares the Principled BSDF inputs plus any image texture bound to Base Color,
    which is what a KiCad VRML export actually produces.
    """
    if mat is None or not mat.use_nodes:
        return None

    bsdf_inputs = None
    for node in mat.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            bsdf_inputs = node.inputs
            break

    if bsdf_inputs is None:
        return None

    def _inp(key):
        sock = bsdf_inputs.get(key)
        if sock is None:
            return None
        val = getattr(sock, "default_value", None)
        if val is None:
            return None
        try:
            return tuple(round(float(c), 6) for c in val)
        except TypeError:
            return round(float(val), 6)

    # Collect image textures separately (names/filepaths), then fold into the signature.
    images = []
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            images.append((node.image.name, node.image.filepath, node.interpolation))

    return (
        _inp("Base Color"),
        _inp("Metallic"),
        _inp("Roughness"),
        _inp("Alpha"),
        _inp("Emission Color"),
        _inp("Coat Weight"),
        tuple(sorted(images)),
    )


def deduplicate_component_materials(objects=None):
    """
    Collapses truly duplicated materials (e.g. Shape.001, Shape.002) back onto their
    master base material (Shape) and purges the now-unused duplicates.

    KiCad's VRML export inlines every material as its own datablock, so one import can
    produce hundreds of materials that bloat the .blend and make shading inconsistent.

    SAFETY: KiCad names the *distinct* board layer materials flat as Shape, Shape.001,
    Shape.002 ... (copper, tin, mask, silkscreen). Those are NOT duplicates. So a numeric
    suffix alone is never enough to merge two materials — the base material must also be
    shading-equivalent (same Principled inputs and same image textures). Anything that
    differs is left completely untouched.

    objects: optional iterable of objects to limit the scan to. Pass the newly imported
        PCB objects so a user's own models are never touched. Defaults to all objects
        for manual/back-compat use.
    Returns: (reassigned_slots, purged_orphan_materials)
    """
    target_objs = objects if objects is not None else bpy.data.objects

    # Cache signatures once per material instead of per slot (RNA reads are not free).
    sig_cache = {}

    def signature(name):
        if name not in sig_cache:
            mat = bpy.data.materials.get(name)
            sig_cache[name] = _material_signature(mat) if mat else None
        return sig_cache[name]

    reassigned = 0
    emptied = []
    for obj in target_objs:
        if obj.type != 'MESH':
            continue
        for slot in obj.material_slots:
            mat = slot.material
            if not mat:
                continue
            mat_name = mat.name
            # Only a trailing numeric suffix counts as a duplicate marker
            # ("Shape.001" -> "Shape"); a dot in a legitimate name does not.
            if "." not in mat_name:
                continue
            base_name, _, suffix = mat_name.rpartition(".")
            if not base_name or not suffix.isdigit():
                continue
            base_mat = bpy.data.materials.get(base_name)
            if base_mat is None:
                continue
            # Equivalence guard: only merge visually identical materials.
            base_sig, dup_sig = signature(base_name), signature(mat_name)
            if base_sig is None or dup_sig is None or base_sig != dup_sig:
                continue
            slot.material = base_mat
            emptied.append(mat_name)
            reassigned += 1

    # Drop only the duplicates we ourselves emptied, and only if nothing else uses them.
    # Track by NAME, not by RNA reference: the same duplicate can be emptied by several
    # objects, and its struct is invalidated by the first removal.
    purged = 0
    for mat_name in sorted(set(emptied)):
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            continue
        if mat.users == 0 and mat.use_fake_user is False:
            bpy.data.materials.remove(mat)
            purged += 1

    return reassigned, purged

def apply_layer_z_offsets():
    """
    Applies micron-level physical Z offsets to board layers to completely eliminate Z-fighting:
    - Substrate FR4: base (Z=0)
    - Copper / Gold Pads: +0.000035 m (0.035 mm)
    - Solder / Tin Pads:  +0.000045 m (0.045 mm)
    - Solder Mask:        +0.000055 m (0.055 mm)
    - Silkscreen:         +0.000080 m (0.080 mm)
    """
    z_offsets = {
        # Front side (+Z). NOTE: these are applied relative to each object's own
        # current position (see loop below), so the stack stays correct even if the
        # board has been moved or rotated after import.
        "PCB_Copper_Gold_001": 0.000035,
        "PCB_Solder_Tin_002":  0.000045,
        "PCB_SolderMask_003":  0.000055,
        "PCB_Silkscreen_008":  0.000080,
        "PCB_Silkscreen":      0.000080,
        
        # Back side (-Z)
        "PCB_Copper_Gold_004": -0.000035,
        "PCB_Solder_Tin_005":  -0.000045,
        "PCB_SolderMask_006":  -0.000055,
        "PCB_Solder_Tin_007":  -0.000045,
        "PCB_Silkscreen_009":  -0.000080,
    }
    
    # Board local +Z in world space. Layer offsets are physical distances along this
    # axis, so they must follow the board. Using absolute world Z silently inverts the
    # stack order if the user rotates the board after import.
    board_up = mathutils.Vector((0.0, 0.0, 1.0))
    substrate = bpy.data.objects.get("PCB_Substrate_FR4")
    if substrate:
        board_up = (substrate.matrix_world.to_3x3() @ mathutils.Vector((0.0, 0.0, 1.0))).normalized()

    for obj_name, z_val in z_offsets.items():
        obj = bpy.data.objects.get(obj_name)
        if obj:
            # Offset along the board normal, preserving the in-plane position.
            plane_offset = obj.location.dot(board_up)
            obj.location = obj.location + board_up * (z_val - plane_offset)

def get_component_category(ref):
    """Classifies a component reference into a user-friendly category collection"""
    prefix = ''.join([c for c in ref if c.isalpha()]).upper()
    cat_map = {
        'C': '01_Capacitors',
        'R': '02_Resistors',
        'RN': '02_Resistors',
        'U': '03_Integrated_Circuits',
        'IC': '03_Integrated_Circuits',
        'Q': '04_Transistors_FETs',
        'D': '05_Diodes_LEDs',
        'LED': '05_Diodes_LEDs',
        'SW': '06_Switches_Buttons',
        'BTN': '06_Switches_Buttons',
        'J': '07_Connectors_Headers',
        'P': '07_Connectors_Headers',
        'Y': '08_Crystals_Oscillators',
        'X': '08_Crystals_Oscillators',
        'L': '09_Inductors',
        'FB': '09_Inductors',
        'TP': '10_Test_Points',
        'LS': '11_Audio_Buzzers',
        'BZ': '11_Audio_Buzzers',
        'F': '12_Fuses',
        'BT': '13_Batteries',
    }
    return cat_map.get(prefix, '14_Other_Components')

def organize_into_collections(pcb_new_objects, soldermask_preset='GREEN', use_pbr_materials=False):
    """
    Creates structured collections ONLY for the newly imported PCB objects:
    - 01_Board_Substrate (FR4 base)
    - 02_Copper_and_Pads (Gold/Tin pads)
    - 03_Solder_Mask (Solder mask)
    - 04_Silkscreen (White legend print)
    - 05_Components (All SMD & THT electronic parts)
    
    If use_pbr_materials is False (default), original materials & colors directly
    from KiCad (.wrl) are preserved intact for all board layers and components.
    """
    scene = bpy.context.scene
    
    # 1. Master PCB Collection
    pcb_master = bpy.data.collections.get("KiCad_PCB")
    if not pcb_master:
        pcb_master = bpy.data.collections.new("KiCad_PCB")
        scene.collection.children.link(pcb_master)
        
    sub_col_names = [
        "01_Board_Substrate",
        "02_Copper_and_Pads",
        "03_Solder_Mask",
        "04_Silkscreen",
        "05_Components"
    ]
    
    sub_cols = {}
    for name in sub_col_names:
        c = bpy.data.collections.get(name)
        if not c:
            c = bpy.data.collections.new(name)
            pcb_master.children.link(c)
        sub_cols[name] = c
        
    # Get PBR Materials only if explicitly requested
    mat_fr4 = None
    mat_soldermask = None
    mat_copper = None
    mat_tin = None
    mat_silk = None
    if use_pbr_materials:
        mat_fr4 = material_engine.setup_fr4_material()
        mat_soldermask = material_engine.setup_soldermask_material(soldermask_preset)
        mat_copper = material_engine.setup_copper_material()
        mat_tin = material_engine.setup_solder_tin_material()
        mat_silk = material_engine.setup_silkscreen_material()
    
    # Process board layers vs components
    for obj in list(pcb_new_objects):
        try:
            if not obj or obj.type != 'MESH':
                continue
        except ReferenceError:
            continue
            
        # Unlink from initial default collection
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
            
        # Check if object is a board layer (Shape_IndexedFaceSet...)
        if obj.name.startswith("Shape_IndexedFaceSet"):
            name = obj.name
            target_mat = None
            if name == "Shape_IndexedFaceSet":
                # Substrate
                sub_cols["01_Board_Substrate"].objects.link(obj)
                obj.name = "PCB_Substrate_FR4"
                target_mat = mat_fr4
            elif name in ["Shape_IndexedFaceSet.001", "Shape_IndexedFaceSet.004"]:
                # Copper tracks / pads
                sub_cols["02_Copper_and_Pads"].objects.link(obj)
                obj.name = f"PCB_Copper_Gold_{name.split('.')[-1]}"
                target_mat = mat_copper
            elif name in ["Shape_IndexedFaceSet.002", "Shape_IndexedFaceSet.005", "Shape_IndexedFaceSet.007"]:
                # Solder / Tin via pads
                sub_cols["02_Copper_and_Pads"].objects.link(obj)
                obj.name = f"PCB_Solder_Tin_{name.split('.')[-1]}"
                target_mat = mat_tin
            elif name in ["Shape_IndexedFaceSet.003", "Shape_IndexedFaceSet.006"]:
                # Solder mask
                sub_cols["03_Solder_Mask"].objects.link(obj)
                obj.name = f"PCB_SolderMask_{name.split('.')[-1]}"
                target_mat = mat_soldermask
            elif name in ["Shape_IndexedFaceSet.008", "Shape_IndexedFaceSet.009"]:
                # Silkscreen
                sub_cols["04_Silkscreen"].objects.link(obj)
                obj.name = f"PCB_Silkscreen_{name.split('.')[-1]}"
                target_mat = mat_silk
            else:
                if len(obj.data.vertices) == 0:
                    bpy.data.objects.remove(obj, do_unlink=True)
                    continue
                else:
                    sub_cols["01_Board_Substrate"].objects.link(obj)
                    
            # Store original imported material for robust restoration
            if obj.data.materials and obj.data.materials[0]:
                obj["kicad_orig_mat_name"] = obj.data.materials[0].name
                obj.data.materials[0].use_fake_user = True
                    
            # Solder mask defaults to authentic Classic Green, other layers keep original file material unless PBR is requested
            if "SolderMask" in obj.name:
                green_mask = material_engine.setup_soldermask_material(soldermask_preset)
                if obj.data.materials:
                    obj.data.materials[0] = green_mask
                else:
                    obj.data.materials.append(green_mask)
            elif use_pbr_materials and target_mat:
                if obj.data.materials:
                    obj.data.materials[0] = target_mat
                else:
                    obj.data.materials.append(target_mat)
        else:
            # Component mesh -> link to 05_Components
            sub_cols["05_Components"].objects.link(obj)

    # Note: Component original materials are kept intact to preserve authentic KiCad 3D colors.

def apply_pbr_materials_to_board(soldermask_preset='GREEN'):
    """Applies custom procedural PBR materials to all board layers on demand"""
    mat_fr4 = material_engine.setup_fr4_material()
    mat_soldermask = material_engine.setup_soldermask_material(soldermask_preset)
    mat_copper = material_engine.setup_copper_material()
    mat_tin = material_engine.setup_solder_tin_material()
    mat_silk = material_engine.setup_silkscreen_material()
    
    applied = 0
    for obj in bpy.data.objects:
        if not obj.name.startswith("PCB_"):
            continue
        target_mat = None
        if "Substrate" in obj.name:
            target_mat = mat_fr4
        elif "Copper" in obj.name:
            target_mat = mat_copper
        elif "Solder_Tin" in obj.name:
            target_mat = mat_tin
        elif "SolderMask" in obj.name:
            target_mat = mat_soldermask
        elif "Silkscreen" in obj.name:
            target_mat = mat_silk
            
        if target_mat:
            if obj.data.materials:
                obj.data.materials[0] = target_mat
            else:
                obj.data.materials.append(target_mat)
            applied += 1
            
    # Redraw 3D Viewport
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
                
    return applied

def restore_original_board_materials():
    """Restores original imported VRML materials and authentic Green solder mask to board layers"""
    vrml_mat_map = {
        "PCB_Substrate_FR4": "Shape",
        "PCB_Copper_Gold_001": "Shape.001",
        "PCB_Solder_Tin_002": "Shape.002",
        "PCB_Copper_Gold_004": "Shape.004",
        "PCB_Solder_Tin_005": "Shape.005",
        "PCB_Solder_Tin_007": "Shape.007",
        "PCB_Silkscreen_008": "Shape.008",
        "PCB_Silkscreen": "Shape.008",
        "PCB_Silkscreen_009": "Shape.009",
    }
    restored = 0
    # 1. Restore substrate, copper/gold, tin/solder, silkscreen to original VRML materials
    for obj_name, default_mat_name in vrml_mat_map.items():
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            continue
        orig_name = obj.get("kicad_orig_mat_name", default_mat_name)
        mat = bpy.data.materials.get(orig_name) or bpy.data.materials.get(default_mat_name)
        if mat:
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
            restored += 1
            
    # 2. Restore solder mask directly to Classic Green so user doesn't have to select green manually!
    green_mask = material_engine.setup_soldermask_material('GREEN')
    for obj in bpy.data.objects:
        if obj.name.startswith("PCB_SolderMask") or "SolderMask" in obj.name:
            if obj.data.materials:
                obj.data.materials[0] = green_mask
            else:
                obj.data.materials.append(green_mask)
            restored += 1

    # Redraw 3D Viewport
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

    return restored

def name_and_classify_components(comp_objs, pcb_filepath):
    """
    Robust spatial clustering and footprint matching:
    1. Comp_objs are evaluated in raw VRML space where coordinates match KiCad mm:
       X_raw = footprint pos_x (mm)
       -Z_raw = footprint pos_y (mm)
    2. Every loose sub-mesh from an inline is assigned to the nearest KiCad footprint center.
    3. All meshes belonging to each footprint are joined into ONE single cohesive object.
    4. Object is renamed to {ref}_{val} (e.g. C16_1uF, R8_470R, U5_RP2040, J1_USB_C).
    5. Each unified component object is placed into its dedicated category sub-collection.
    Returns list of newly joined component objects.
    """
    comp_parent_col = bpy.data.collections.get("05_Components")
    
    fps = {}
    if pcb_filepath and os.path.exists(pcb_filepath):
        fps = pcb_parser.parse_kicad_pcb(pcb_filepath)
        
    if not fps:
        # If no PCB file, just return existing comp_objs
        return list(comp_objs)
        
    # Exact spatial clustering of meshes to footprint coordinates
    fp_to_objs = {ref: [] for ref in fps}
    unmatched = []
    
    for obj in comp_objs:
        if not obj or obj.type != 'MESH':
            continue
            
        # In raw VRML space, obj.location.x matches pos_x, -obj.location.z matches pos_y
        lx = obj.location.x
        ly = -obj.location.z
        
        best_ref = None
        min_dist = float('inf')
        for ref, data in fps.items():
            d = ((data['pos_x'] - lx)**2 + (data['pos_y'] - ly)**2)**0.5
            if d < min_dist:
                min_dist = d
                best_ref = ref
                
        if best_ref and min_dist < 0.5:  # Exact match within 0.5mm
            fp_to_objs[best_ref].append(obj)
        else:
            unmatched.append(obj)
            
    # Now join all meshes belonging to each component into a single object
    cat_cols = {}
    joined_component_objects = []
    
    for ref, group in fp_to_objs.items():
        if not group:
            continue
            
        target = group[0]
        if len(group) > 1:
            try:
                with bpy.context.temp_override(
                    active_object=target,
                    selected_objects=group,
                    selected_editable_objects=group
                ):
                    bpy.ops.object.join()
            except Exception as e:
                print(f"[KiCad PCB Tools] Warning: Failed to join objects for {ref}: {e}")
                
        val = fps[ref]['val']
        obj_name = f"{ref}_{val}" if val else ref
        target.name = obj_name
        
        target["kicad_reference"] = ref
        target["kicad_value"] = val
        target["kicad_footprint"] = fps[ref]['fp_name']
        
        # Categorize into sub-collection
        if comp_parent_col:
            cat_name = get_component_category(ref)
            if cat_name not in cat_cols:
                cat_c = bpy.data.collections.get(cat_name)
                if not cat_c:
                    cat_c = bpy.data.collections.new(cat_name)
                    comp_parent_col.children.link(cat_c)
                cat_cols[cat_name] = cat_c
                
            # Move target into category collection
            for c in list(target.users_collection):
                c.objects.unlink(target)
            cat_cols[cat_name].objects.link(target)
            
        joined_component_objects.append(target)
        
    # Any unmatched meshes remain in 05_Components
    for obj in unmatched:
        joined_component_objects.append(obj)
        
    return joined_component_objects
