import bpy

def get_or_create_pbr_component_materials():
    """Returns or creates the standard set of master PBR component materials"""
    mats = {}
    
    # 1. Molded Epoxy IC Body
    mat = bpy.data.materials.get("KiCad_IC_Body_Epoxy")
    if not mat:
        mat = bpy.data.materials.new("KiCad_IC_Body_Epoxy")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.148, 0.145, 0.145, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.55
            bsdf.inputs['Metallic'].default_value = 0.0
            if 'Specular IOR Level' in bsdf.inputs:
                bsdf.inputs['Specular IOR Level'].default_value = 0.45
            elif 'Specular' in bsdf.inputs:
                bsdf.inputs['Specular'].default_value = 0.45
    mats['ic_body'] = mat
    
    # 2. Pin / Solder Tin
    mat = bpy.data.materials.get("KiCad_Component_Pin_Tin")
    if not mat:
        mat = bpy.data.materials.new("KiCad_Component_Pin_Tin")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.824, 0.820, 0.781, 1.0)
            bsdf.inputs['Metallic'].default_value = 0.95
            bsdf.inputs['Roughness'].default_value = 0.20
            if 'Specular IOR Level' in bsdf.inputs:
                bsdf.inputs['Specular IOR Level'].default_value = 0.5
    mats['pin_tin'] = mat
    
    # 3. Ceramic Capacitor Body
    mat = bpy.data.materials.get("KiCad_Capacitor_Ceramic")
    if not mat:
        mat = bpy.data.materials.new("KiCad_Capacitor_Ceramic")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.379, 0.270, 0.215, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.40
            bsdf.inputs['Metallic'].default_value = 0.0
            if 'Specular IOR Level' in bsdf.inputs:
                bsdf.inputs['Specular IOR Level'].default_value = 0.45
    mats['cap_ceramic'] = mat
    
    # 4. Resistor Glaze Body
    mat = bpy.data.materials.get("KiCad_Resistor_Body")
    if not mat:
        mat = bpy.data.materials.new("KiCad_Resistor_Body")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.082, 0.086, 0.094, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.28
            bsdf.inputs['Metallic'].default_value = 0.0
            if 'Specular IOR Level' in bsdf.inputs:
                bsdf.inputs['Specular IOR Level'].default_value = 0.5
    mats['res_body'] = mat
    
    # 5. Marking White
    mat = bpy.data.materials.get("KiCad_Component_Marking_White")
    if not mat:
        mat = bpy.data.materials.new("KiCad_Component_Marking_White")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.90, 0.90, 0.90, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.50
            bsdf.inputs['Metallic'].default_value = 0.0
    mats['marking_white'] = mat
    
    # 6. Potentiometer Blue Plastic Body
    mat = bpy.data.materials.get("KiCad_Pot_Body_Blue")
    if not mat:
        mat = bpy.data.materials.new("KiCad_Pot_Body_Blue")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.03, 0.20, 0.65, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.35
            bsdf.inputs['Metallic'].default_value = 0.0
    mats['pot_blue'] = mat
    
    # 7. Potentiometer Metal Shaft
    mat = bpy.data.materials.get("KiCad_Metal_Shaft")
    if not mat:
        mat = bpy.data.materials.new("KiCad_Metal_Shaft")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.75, 0.76, 0.78, 1.0)
            bsdf.inputs['Metallic'].default_value = 0.90
            bsdf.inputs['Roughness'].default_value = 0.32
    mats['metal_shaft'] = mat
    
    return mats

def detect_scene_component_materials():
    """
    Scans existing imported PCB components in the scene to find active
    materials for IC body epoxy, pin solder/tin, capacitor ceramic, and resistor body.
    Returns dict of {category: bpy.types.Material}.
    """
    detected = {
        'ic_body': None,
        'pin_tin': None,
        'cap_ceramic': None,
        'res_body': None,
        'marking_white': None,
        'pot_blue': None,
        'metal_shaft': None,
    }
    
    # 1. Prefer existing Master PBR materials if they exist in the scene
    pbr_mats = get_or_create_pbr_component_materials()
    
    # 2. Check existing components to see what materials they actually use
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        ref = obj.get("kicad_reference", "")
        if not ref:
            continue
            
        # Check IC components (U..., Q..., IC...)
        if ref.startswith(('U', 'IC', 'Q')) and not detected['ic_body']:
            for slot in obj.material_slots:
                if not slot.material or not slot.material.use_nodes:
                    continue
                mat = slot.material
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf and 'Base Color' in bsdf.inputs:
                    col = bsdf.inputs['Base Color'].default_value
                    # Dark grey / black body (luminance < 0.25)
                    luminance = 0.299 * col[0] + 0.587 * col[1] + 0.114 * col[2]
                    if luminance < 0.25 and not detected['ic_body']:
                        detected['ic_body'] = mat
                    # Bright tin / silver pin
                    elif luminance > 0.70 and not detected['pin_tin']:
                        detected['pin_tin'] = mat
                        
        # Check Capacitor components (C...)
        if ref.startswith('C') and not detected['cap_ceramic']:
            for slot in obj.material_slots:
                if not slot.material or not slot.material.use_nodes:
                    continue
                mat = slot.material
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf and 'Base Color' in bsdf.inputs:
                    col = bsdf.inputs['Base Color'].default_value
                    # Tan / brownish ceramic: red > blue, moderate luminance
                    if col[0] > col[2] and 0.20 < col[0] < 0.65:
                        detected['cap_ceramic'] = mat
                    elif col[0] > 0.70 and not detected['pin_tin']:
                        detected['pin_tin'] = mat
                        
        # Check Resistor components (R...)
        if ref.startswith('R') and not detected['res_body']:
            for slot in obj.material_slots:
                if not slot.material or not slot.material.use_nodes:
                    continue
                mat = slot.material
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf and 'Base Color' in bsdf.inputs:
                    col = bsdf.inputs['Base Color'].default_value
                    luminance = 0.299 * col[0] + 0.587 * col[1] + 0.114 * col[2]
                    if luminance < 0.15:
                        detected['res_body'] = mat
                        
    # Fallback to standard PBR materials for any undetected slot
    for key, mat in pbr_mats.items():
        if not detected.get(key):
            detected[key] = mat
            
    return detected

def apply_harmonized_materials(obj, package_name, scene_mats=None):
    """
    Connects the material slots of a newly placed component to the active scene
    materials so it perfectly matches the shading, epoxy black tone, and metal
    specularity of the rest of the board.

    scene_mats: optional precomputed palette from detect_scene_component_materials().
        Pass it when placing a batch to avoid a full scene rescan per component.
        When omitted, the palette is detected as before.
    """
    if not obj or obj.type != 'MESH':
        return

    if scene_mats is None:
        scene_mats = detect_scene_component_materials()
    
    is_resistor = package_name.startswith("R_")
    is_capacitor = package_name.startswith("C_")
    is_ic_or_discrete = package_name in ["SOIC-8", "TSSOP-8", "SOIC-16", "SOT-23", "SOT-23-6", "SOT-223", "TO-252", "QFN-32", "IND_5050"]
    is_pot = package_name.startswith("POT_")
    is_switch = "SW_" in package_name
    
    if is_resistor:
        # Slot 0: pin_tin, Slot 1: res_body
        if len(obj.data.materials) > 0 and scene_mats['pin_tin']:
            obj.data.materials[0] = scene_mats['pin_tin']
        if len(obj.data.materials) > 1 and scene_mats['res_body']:
            obj.data.materials[1] = scene_mats['res_body']
            
    elif is_capacitor:
        # Slot 0: pin_tin, Slot 1: cap_ceramic
        if len(obj.data.materials) > 0 and scene_mats['pin_tin']:
            obj.data.materials[0] = scene_mats['pin_tin']
        if len(obj.data.materials) > 1 and scene_mats['cap_ceramic']:
            obj.data.materials[1] = scene_mats['cap_ceramic']
            
    elif is_ic_or_discrete:
        # Slot 0: ic_body, Slot 1: pin_tin, Slot 2: marking_white
        if len(obj.data.materials) > 0 and scene_mats['ic_body']:
            obj.data.materials[0] = scene_mats['ic_body']
        if len(obj.data.materials) > 1 and scene_mats['pin_tin']:
            obj.data.materials[1] = scene_mats['pin_tin']
        if len(obj.data.materials) > 2 and scene_mats['marking_white']:
            obj.data.materials[2] = scene_mats['marking_white']
            
    elif is_pot:
        # Slot 0: pot_blue, Slot 1: metal_shaft, Slot 2: pin_tin
        if len(obj.data.materials) > 0 and scene_mats.get('pot_blue'):
            obj.data.materials[0] = scene_mats['pot_blue']
        if len(obj.data.materials) > 1 and scene_mats.get('metal_shaft'):
            obj.data.materials[1] = scene_mats['metal_shaft']
        if len(obj.data.materials) > 2 and scene_mats['pin_tin']:
            obj.data.materials[2] = scene_mats['pin_tin']
            
    elif is_switch:
        # Slot 0: pin_tin (metal case), Slot 1: ic_body (black knob)
        if len(obj.data.materials) > 0 and scene_mats['pin_tin']:
            obj.data.materials[0] = scene_mats['pin_tin']
        if len(obj.data.materials) > 1 and scene_mats['ic_body']:
            obj.data.materials[1] = scene_mats['ic_body']

def harmonize_all_components():
    """
    Unifies shader materials across all components in the scene (both original
    imported VRML components and newly added library components) so that all
    IC bodies share the same molded epoxy shader, all pins share the same solder
    tin shader, and all passives share identical ceramic/resistor materials.
    """
    master_mats = get_or_create_pbr_component_materials()
    updated_count = 0
    
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        ref = obj.get("kicad_reference", "")
        if not ref and not obj.name.startswith(("Component_", "C", "R", "U", "Q", "J")):
            continue
            
        # Classify component
        is_r = ref.startswith('R')
        is_c = ref.startswith('C')
        is_ic = ref.startswith(('U', 'Q', 'IC')) or any(k in obj.name for k in ["SOIC", "SOT", "QFN", "TO252"])
        
        for i, slot in enumerate(obj.material_slots):
            if not slot.material or not slot.material.use_nodes:
                continue
            bsdf = slot.material.node_tree.nodes.get("Principled BSDF")
            if not bsdf or 'Base Color' not in bsdf.inputs:
                continue
            col = bsdf.inputs['Base Color'].default_value
            lum = 0.299 * col[0] + 0.587 * col[1] + 0.114 * col[2]
            
            # Pin contacts / metal pads
            if lum > 0.70:
                slot.material = master_mats['pin_tin']
                updated_count += 1
            # IC Molded Epoxy body
            elif is_ic and lum < 0.30:
                slot.material = master_mats['ic_body']
                updated_count += 1
            # Capacitor ceramic body
            elif is_c and 0.20 < lum < 0.65 and col[0] > col[2]:
                slot.material = master_mats['cap_ceramic']
                updated_count += 1
            # Resistor body
            elif is_r and lum < 0.20:
                slot.material = master_mats['res_body']
                updated_count += 1
                
    return updated_count
