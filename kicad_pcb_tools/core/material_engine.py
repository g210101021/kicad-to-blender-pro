import bpy

# Solder mask preset color palettes (Linear RGB)
SOLDERMASK_PALETTES = {
    'GREEN': {
        'name': 'Classic Green',
        'base_color': (0.008, 0.125, 0.045, 1.0),
        'subsurface_color': (0.015, 0.25, 0.08, 1.0),
        'roughness': 0.22,
        'specular': 0.5,
        'transmission': 0.15
    },
    'MATTE_BLACK': {
        'name': 'Matte Black',
        'base_color': (0.015, 0.015, 0.015, 1.0),
        'subsurface_color': (0.02, 0.02, 0.02, 1.0),
        'roughness': 0.55,
        'specular': 0.35,
        'transmission': 0.0
    },
    'GLOSSY_BLACK': {
        'name': 'Glossy Black',
        'base_color': (0.01, 0.01, 0.01, 1.0),
        'subsurface_color': (0.015, 0.015, 0.015, 1.0),
        'roughness': 0.15,
        'specular': 0.6,
        'transmission': 0.05
    },
    'BLUE': {
        'name': 'Royal Blue',
        'base_color': (0.008, 0.045, 0.25, 1.0),
        'subsurface_color': (0.015, 0.08, 0.4, 1.0),
        'roughness': 0.2,
        'specular': 0.5,
        'transmission': 0.12
    },
    'PURPLE': {
        'name': 'OSH Park Purple',
        'base_color': (0.075, 0.015, 0.16, 1.0),
        'subsurface_color': (0.12, 0.03, 0.25, 1.0),
        'roughness': 0.22,
        'specular': 0.5,
        'transmission': 0.15
    },
    'RED': {
        'name': 'Ruby Red',
        'base_color': (0.35, 0.01, 0.015, 1.0),
        'subsurface_color': (0.55, 0.02, 0.03, 1.0),
        'roughness': 0.2,
        'specular': 0.5,
        'transmission': 0.12
    },
    'WHITE': {
        'name': 'Ceramic White',
        'base_color': (0.88, 0.88, 0.88, 1.0),
        'subsurface_color': (0.95, 0.95, 0.95, 1.0),
        'roughness': 0.3,
        'specular': 0.45,
        'transmission': 0.0
    }
}

def get_or_create_material(name):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
    else:
        mat.use_nodes = True
    return mat

def setup_fr4_material():
    """Creates/configures the FR4 Substrate epoxy-glass material"""
    mat = get_or_create_material("KiCad_FR4_Substrate")
    tree = mat.node_tree
    tree.nodes.clear()
    
    output = tree.nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    bsdf = tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    # FR4 dark olive / amber greenish composite look
    if 'Base Color' in bsdf.inputs:
        bsdf.inputs['Base Color'].default_value = (0.045, 0.05, 0.03, 1.0)
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = 0.55
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.3
    elif 'Specular' in bsdf.inputs:
        bsdf.inputs['Specular'].default_value = 0.3
        
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def setup_soldermask_material(preset='GREEN'):
    """Creates/configures realistic semi-translucent solder mask"""
    preset_data = SOLDERMASK_PALETTES.get(preset, SOLDERMASK_PALETTES['GREEN'])
    mat = get_or_create_material(f"KiCad_SolderMask_{preset}")
    tree = mat.node_tree
    tree.nodes.clear()
    
    output = tree.nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    bsdf = tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    if 'Base Color' in bsdf.inputs:
        bsdf.inputs['Base Color'].default_value = preset_data['base_color']
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = preset_data['roughness']
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = preset_data['specular']
    elif 'Specular' in bsdf.inputs:
        bsdf.inputs['Specular'].default_value = preset_data['specular']
    if 'Transmission Weight' in bsdf.inputs:
        bsdf.inputs['Transmission Weight'].default_value = preset_data['transmission']
    elif 'Transmission' in bsdf.inputs:
        bsdf.inputs['Transmission'].default_value = preset_data['transmission']
        
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def setup_copper_material():
    """
    Creates physically accurate, unexaggerated PCB Copper foil material.
    Based on real-world industrial optical measurements of rolled-annealed (RA)
    and electrodeposited (ED) PCB copper foil with standard anti-tarnish micro-passivation.
    - Linear RGB Base Color: (0.96, 0.48, 0.26, 1.0)
    - Metallic: 1.0 (pure conductive metal)
    - Roughness: 0.22 (authentic smooth satin foil sheen, no exaggerated artificial bumps)
    - Specular IOR Level: 0.5
    """
    mat = get_or_create_material("KiCad_Copper")
    tree = mat.node_tree
    tree.nodes.clear()
    
    output = tree.nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    bsdf = tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    if 'Base Color' in bsdf.inputs:
        bsdf.inputs['Base Color'].default_value = (0.96, 0.48, 0.26, 1.0)
    if 'Metallic' in bsdf.inputs:
        bsdf.inputs['Metallic'].default_value = 1.0
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = 0.22
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.5
    elif 'Specular' in bsdf.inputs:
        bsdf.inputs['Specular'].default_value = 0.5
        
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def setup_copper_gold_material(is_gold=False):
    """Creates ENIG (Gold) or physically accurate bare copper material"""
    if not is_gold:
        return setup_copper_material()
        
    mat = get_or_create_material("KiCad_ENIG_Gold")
    tree = mat.node_tree
    tree.nodes.clear()
    
    output = tree.nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    bsdf = tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    # ENIG Gold Color
    if 'Base Color' in bsdf.inputs:
        bsdf.inputs['Base Color'].default_value = (0.85, 0.65, 0.22, 1.0)
    if 'Metallic' in bsdf.inputs:
        bsdf.inputs['Metallic'].default_value = 1.0
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = 0.22
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.5
    elif 'Specular' in bsdf.inputs:
        bsdf.inputs['Specular'].default_value = 0.5
        
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def setup_solder_tin_material():
    """Creates HASL lead-free solder tin / via fill material"""
    mat = get_or_create_material("KiCad_Solder_Tin")
    tree = mat.node_tree
    tree.nodes.clear()
    
    output = tree.nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    bsdf = tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    # Shiny silvery tin solder
    if 'Base Color' in bsdf.inputs:
        bsdf.inputs['Base Color'].default_value = (0.75, 0.76, 0.78, 1.0)
    if 'Metallic' in bsdf.inputs:
        bsdf.inputs['Metallic'].default_value = 0.95
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = 0.18
        
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def setup_silkscreen_material():
    """Creates matte white silkscreen printing material"""
    mat = get_or_create_material("KiCad_Silkscreen_White")
    tree = mat.node_tree
    tree.nodes.clear()
    
    output = tree.nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    bsdf = tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    if 'Base Color' in bsdf.inputs:
        bsdf.inputs['Base Color'].default_value = (0.92, 0.92, 0.92, 1.0)
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = 0.45
    if 'Metallic' in bsdf.inputs:
        bsdf.inputs['Metallic'].default_value = 0.0
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.4
    elif 'Specular' in bsdf.inputs:
        bsdf.inputs['Specular'].default_value = 0.4
        
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat
