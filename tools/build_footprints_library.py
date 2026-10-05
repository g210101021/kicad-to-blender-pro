import bpy
import bmesh
import math
import os

def create_shared_materials():
    """Creates or retrieves shared PBR materials for all footprint packages"""
    mats = {}
    
    # 1. IC Body Molded Epoxy
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
    
    # 2. Pin / Terminal Solder Tin
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
    
    # 3. MLCC Capacitor Ceramic (Tan / Light Buff)
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
    
    # 4. Resistor Glazed Body
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
    
    # 5. Silkscreen / Laser Marking White
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

def add_box(bm, center, size, mat_index):
    """Helper to cleanly create a box with center (x,y,z), size (sx, sy, sz) and material index"""
    res = bmesh.ops.create_cube(bm, size=1.0)
    verts = res['verts']
    sx, sy, sz = size
    cx, cy, cz = center
    for v in verts:
        v.co.x = cx + v.co.x * sx
        v.co.y = cy + v.co.y * sy
        v.co.z = cz + v.co.z * sz
    for f in bm.faces:
        if all(v in verts for v in f.verts):
            f.material_index = mat_index
    return verts

def build_smd_chip(name, length_mm, width_mm, height_mm, band_mm, is_resistor, mats):
    """
    Builds a standard 2-terminal SMD chip (0402, 0603, 0805, 1206).
    Length along X (pin 1 at -X, pin 2 at +X), width along Y, height along Z.
    Center is at (0, 0, 0) in XY, Z=0 is bottom seating surface.
    """
    L = length_mm * 0.001
    W = width_mm * 0.001
    H = height_mm * 0.001
    B = band_mm * 0.001
    
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    body_mat = mats['res_body'] if is_resistor else mats['cap_ceramic']
    tin_mat = mats['pin_tin']
    
    # 1. Left Cap (tin, mat_index=0) at -X
    add_box(bm, center=(-L/2 + B/2, 0.0, H/2), size=(B, W, H), mat_index=0)
    
    # 2. Center Body (body, mat_index=1)
    body_len = L - 2 * B
    add_box(bm, center=(0.0, 0.0, H/2), size=(body_len, W, H), mat_index=1)
    
    # 3. Right Cap (tin, mat_index=0) at +X
    add_box(bm, center=(L/2 - B/2, 0.0, H/2), size=(B, W, H), mat_index=0)
    
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000005)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(tin_mat)
    obj.data.materials.append(body_mat)
    
    bev = obj.modifiers.new("Bevel", type='BEVEL')
    bev.width = min(W, H) * 0.08
    bev.segments = 2
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(40)
    
    return obj

def build_gullwing_lead_curved(bm, r_inner, r_outer, body_z, width, thick, dir_sign=1.0, perp_pos=0.0, axis="x", mat_index=1):
    """
    Generates a realistic curved gullwing lead matching KiCad official 3D models (U6 SOIC / U11 TSSOP):
    - Smooth shoulder emerging horizontally from IC body
    - Curved convex knee
    - Slanted leg descent
    - Curved concave ankle
    - Horizontal flat solder foot seating on PCB pad (Z=0)
    """
    span = abs(r_outer - r_inner)
    foot_len = max(span * 0.45, 0.35 * 0.001)
    shoulder_len = span * 0.18
    
    r0 = r_inner
    r1 = r_inner + shoulder_len
    r4 = r_outer - foot_len
    r5 = r_outer
    r2 = r1 + (r4 - r1) * 0.35
    r3 = r1 + (r4 - r1) * 0.70
    
    z0 = body_z - thick
    z1 = body_z - thick
    z2 = body_z - thick - (body_z - thick) * 0.25
    z3 = thick * 0.8
    z4 = 0.0
    z5 = 0.0
    
    bot = [(r0, z0), (r1, z1), (r2, z2), (r3, z3), (r4, z4), (r5, z5)]
    top = [(r0, z0 + thick), (r1, z1 + thick), (r2, z2 + thick), (r3, z3 + thick), (r4, z4 + thick), (r5, z5 + thick)]
    
    w_half = width / 2.0
    bot_v_neg, bot_v_pos = [], []
    top_v_neg, top_v_pos = [], []
    
    for (r, z) in bot:
        coord_r = dir_sign * r
        if axis == "x":
            v1 = bm.verts.new((coord_r, perp_pos - w_half, z))
            v2 = bm.verts.new((coord_r, perp_pos + w_half, z))
        else:
            v1 = bm.verts.new((perp_pos - w_half, coord_r, z))
            v2 = bm.verts.new((perp_pos + w_half, coord_r, z))
        bot_v_neg.append(v1)
        bot_v_pos.append(v2)
        
    for (r, z) in top:
        coord_r = dir_sign * r
        if axis == "x":
            v1 = bm.verts.new((coord_r, perp_pos - w_half, z))
            v2 = bm.verts.new((coord_r, perp_pos + w_half, z))
        else:
            v1 = bm.verts.new((perp_pos - w_half, coord_r, z))
            v2 = bm.verts.new((perp_pos + w_half, coord_r, z))
        top_v_neg.append(v1)
        top_v_pos.append(v2)
        
    N = len(bot)
    faces = []
    # Bottom strip
    for i in range(N - 1):
        if dir_sign > 0:
            f = bm.faces.new((bot_v_neg[i], bot_v_pos[i], bot_v_pos[i+1], bot_v_neg[i+1]))
        else:
            f = bm.faces.new((bot_v_neg[i], bot_v_neg[i+1], bot_v_pos[i+1], bot_v_pos[i]))
        f.material_index = mat_index
        faces.append(f)
    # Top strip
    for i in range(N - 1):
        if dir_sign > 0:
            f = bm.faces.new((top_v_pos[i], top_v_neg[i], top_v_neg[i+1], top_v_pos[i+1]))
        else:
            f = bm.faces.new((top_v_pos[i], top_v_pos[i+1], top_v_neg[i+1], top_v_neg[i]))
        f.material_index = mat_index
        faces.append(f)
    # Side 1 (-w)
    for i in range(N - 1):
        if dir_sign > 0:
            f = bm.faces.new((bot_v_neg[i], bot_v_neg[i+1], top_v_neg[i+1], top_v_neg[i]))
        else:
            f = bm.faces.new((bot_v_neg[i], top_v_neg[i], top_v_neg[i+1], bot_v_neg[i+1]))
        f.material_index = mat_index
        faces.append(f)
    # Side 2 (+w)
    for i in range(N - 1):
        if dir_sign > 0:
            f = bm.faces.new((bot_v_pos[i], top_v_pos[i], top_v_pos[i+1], bot_v_pos[i+1]))
        else:
            f = bm.faces.new((bot_v_pos[i], bot_v_pos[i+1], top_v_pos[i+1], top_v_pos[i]))
        f.material_index = mat_index
        faces.append(f)
    # End cap (tip at N-1)
    if dir_sign > 0:
        f = bm.faces.new((bot_v_neg[-1], bot_v_pos[-1], top_v_pos[-1], top_v_neg[-1]))
    else:
        f = bm.faces.new((bot_v_pos[-1], bot_v_neg[-1], top_v_neg[-1], top_v_pos[-1]))
    f.material_index = mat_index
    faces.append(f)
    # Start cap (at 0)
    if dir_sign > 0:
        f = bm.faces.new((bot_v_pos[0], bot_v_neg[0], top_v_neg[0], top_v_pos[0]))
    else:
        f = bm.faces.new((bot_v_neg[0], bot_v_pos[0], top_v_pos[0], top_v_neg[0]))
    f.material_index = mat_index
    faces.append(f)
    
    return faces

def build_soic(name, num_pins, body_len_mm, body_wid_mm, total_wid_mm, height_mm, pitch_mm, mats):
    """
    Builds SOIC-8 or SOIC-16 IC package according to KiCad / IPC-7351 standards:
    - Body length along Y axis.
    - Body width along X axis.
    - Curved gullwing leads copied from U6.
    - Pin 1 dot is at (-X, +Y) -> Top-Left in Blender!
    """
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    Lx = body_wid_mm * 0.001
    Ly = body_len_mm * 0.001
    H = height_mm * 0.001
    standoff = 0.15 * 0.001
    body_h = H - standoff
    
    # 1. Molded Body (mat_index=0)
    add_box(bm, center=(0.0, 0.0, standoff + body_h / 2.0), size=(Lx, Ly, body_h), mat_index=0)
    
    # 2. Pin 1 Dot Marker on top face (mat_index=2) at (-X, +Y) -> Top-Left!
    dot_radius = 0.35 * 0.001
    dot_x = -Lx/2 + 0.70 * 0.001
    dot_y = +Ly/2 - 0.70 * 0.001
    dot_z = H + 0.00001
    
    res = bmesh.ops.create_circle(bm, cap_ends=True, radius=dot_radius, segments=12)
    for v in res['verts']:
        v.co.x += dot_x
        v.co.y += dot_y
        v.co.z += dot_z
    for f in bm.faces:
        if all(v in res['verts'] for v in f.verts):
            f.material_index = 2
            
    # 3. Curved Gullwing Pins along X axis (matching U6)
    pins_per_side = num_pins // 2
    y_start = +((pins_per_side - 1) * pitch_mm) / 2.0
    x_inner = (body_wid_mm / 2.0) * 0.001
    x_outer = (total_wid_mm / 2.0) * 0.001
    z_mid = height_mm * 0.5 * 0.001
    
    for i in range(pins_per_side):
        y = y_start - i * pitch_mm
        # Left side (-X): Pin 1 .. N/2
        build_gullwing_lead_curved(bm, x_inner, x_outer, z_mid, width=0.42*0.001, thick=0.18*0.001, dir_sign=-1.0, perp_pos=y*0.001, axis="x", mat_index=1)
        # Right side (+X): Pin N .. N/2+1
        build_gullwing_lead_curved(bm, x_inner, x_outer, z_mid, width=0.42*0.001, thick=0.18*0.001, dir_sign=1.0, perp_pos=y*0.001, axis="x", mat_index=1)
        
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000005)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mats['ic_body'])
    obj.data.materials.append(mats['pin_tin'])
    obj.data.materials.append(mats['marking_white'])
    
    bev = obj.modifiers.new("Bevel", type='BEVEL')
    bev.width = 0.00008
    bev.segments = 2
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(45)
    
    return obj

def build_tssop8(name, mats):
    """
    Builds TSSOP-8 with 0.65 mm pitch (for FS8205A, etc.) matching U11:
    - Body length: 3.0 mm along Y.
    - Body width: 3.0 mm along X (total span with pins: 6.4 mm).
    - Pitch: 0.65 mm.
    - Pin 1 dot at (-X, +Y).
    """
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    Lx = 3.00 * 0.001
    Ly = 3.00 * 0.001
    H = 1.10 * 0.001
    standoff = 0.10 * 0.001
    body_h = H - standoff
    
    # Body
    add_box(bm, center=(0.0, 0.0, standoff + body_h / 2.0), size=(Lx, Ly, body_h), mat_index=0)
    
    # Pin 1 Dot Marker at (-X, +Y)
    dot_radius = 0.28 * 0.001
    dot_x = -Lx/2 + 0.50 * 0.001
    dot_y = +Ly/2 - 0.50 * 0.001
    dot_z = H + 0.00001
    res = bmesh.ops.create_circle(bm, cap_ends=True, radius=dot_radius, segments=12)
    for v in res['verts']:
        v.co.x += dot_x
        v.co.y += dot_y
        v.co.z += dot_z
    for f in bm.faces:
        if all(v in res['verts'] for v in f.verts):
            f.material_index = 2
            
    # 4 pins per side along X axis, pitch 0.65 mm (matching U11 TSSOP leads)
    x_inner = 1.50 * 0.001
    x_outer = 3.20 * 0.001
    z_mid = 0.55 * 0.001
    for y in [0.975, 0.325, -0.325, -0.975]:
        build_gullwing_lead_curved(bm, x_inner, x_outer, z_mid, width=0.28*0.001, thick=0.14*0.001, dir_sign=-1.0, perp_pos=y*0.001, axis="x", mat_index=1)
        build_gullwing_lead_curved(bm, x_inner, x_outer, z_mid, width=0.28*0.001, thick=0.14*0.001, dir_sign=1.0, perp_pos=y*0.001, axis="x", mat_index=1)
        
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000005)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mats['ic_body'])
    obj.data.materials.append(mats['pin_tin'])
    obj.data.materials.append(mats['marking_white'])
    
    bev = obj.modifiers.new("Bevel", type='BEVEL')
    bev.width = 0.00005
    bev.segments = 2
    return obj

def build_sot23(name, mats):
    """Standard 3-pin SOT-23 (2 pins on -X, 1 pin on +X) with curved leads"""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    Lx = 1.30 * 0.001
    Ly = 2.90 * 0.001
    H = 1.00 * 0.001
    standoff = 0.05 * 0.001
    body_h = H - standoff
    
    add_box(bm, center=(0.0, 0.0, standoff + body_h / 2.0), size=(Lx, Ly, body_h), mat_index=0)
    
    x_inner = 0.65 * 0.001
    x_outer = 1.25 * 0.001
    z_mid = 0.50 * 0.001
    
    build_gullwing_lead_curved(bm, x_inner, x_outer, z_mid, width=0.40*0.001, thick=0.15*0.001, dir_sign=-1.0, perp_pos=0.95*0.001, axis="x", mat_index=1)
    build_gullwing_lead_curved(bm, x_inner, x_outer, z_mid, width=0.40*0.001, thick=0.15*0.001, dir_sign=-1.0, perp_pos=-0.95*0.001, axis="x", mat_index=1)
    build_gullwing_lead_curved(bm, x_inner, x_outer, z_mid, width=0.40*0.001, thick=0.15*0.001, dir_sign=1.0, perp_pos=0.0, axis="x", mat_index=1)
    
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000005)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mats['ic_body'])
    obj.data.materials.append(mats['pin_tin'])
    
    bev = obj.modifiers.new("Bevel", type='BEVEL')
    bev.width = 0.00005
    bev.segments = 2
    return obj

def build_sot23_6(name, mats):
    """
    Builds 6-pin SOT-23-6 / SOT-23-6L (for FP6291 boost converter, etc.):
    - 3 pins on left (-X), 3 pins on right (+X) with curved leads.
    - Pitch: 0.95 mm (y = -0.95, 0.0, +0.95 mm).
    - Pin 1 dot at (-X, +Y).
    """
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    Lx = 1.60 * 0.001
    Ly = 2.90 * 0.001
    H = 1.20 * 0.001
    standoff = 0.08 * 0.001
    body_h = H - standoff
    
    add_box(bm, center=(0.0, 0.0, standoff + body_h / 2.0), size=(Lx, Ly, body_h), mat_index=0)
    
    # Pin 1 Dot
    dot_radius = 0.25 * 0.001
    dot_x = -Lx/2 + 0.40 * 0.001
    dot_y = +Ly/2 - 0.45 * 0.001
    dot_z = H + 0.00001
    res = bmesh.ops.create_circle(bm, cap_ends=True, radius=dot_radius, segments=10)
    for v in res['verts']:
        v.co.x += dot_x
        v.co.y += dot_y
        v.co.z += dot_z
    for f in bm.faces:
        if all(v in res['verts'] for v in f.verts):
            f.material_index = 2
            
    # 3 pins per side along X axis, pitch 0.95 mm
    x_inner = 0.80 * 0.001
    x_outer = 1.40 * 0.001
    z_mid = 0.60 * 0.001
    for y in [0.95, 0.0, -0.95]:
        build_gullwing_lead_curved(bm, x_inner, x_outer, z_mid, width=0.38*0.001, thick=0.15*0.001, dir_sign=-1.0, perp_pos=y*0.001, axis="x", mat_index=1)
        build_gullwing_lead_curved(bm, x_inner, x_outer, z_mid, width=0.38*0.001, thick=0.15*0.001, dir_sign=1.0, perp_pos=y*0.001, axis="x", mat_index=1)
        
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000005)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mats['ic_body'])
    obj.data.materials.append(mats['pin_tin'])
    obj.data.materials.append(mats['marking_white'])
    
    bev = obj.modifiers.new("Bevel", type='BEVEL')
    bev.width = 0.00005
    bev.segments = 2
    return obj

def build_sot223(name, mats):
    """Builds SOT-223 (4-pin tab regulator package) with curved leads"""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    Lx = 3.50 * 0.001
    Ly = 6.50 * 0.001
    H = 1.60 * 0.001
    standoff = 0.08 * 0.001
    body_h = H - standoff
    
    add_box(bm, center=(0.0, 0.0, standoff + body_h / 2.0), size=(Lx, Ly, body_h), mat_index=0)
    
    x_inner = 1.75 * 0.001
    x_outer = 3.50 * 0.001
    z_mid = 0.80 * 0.001
    for y in [2.30, 0.0, -2.30]:
        build_gullwing_lead_curved(bm, x_inner, x_outer, z_mid, width=0.70*0.001, thick=0.22*0.001, dir_sign=-1.0, perp_pos=y*0.001, axis="x", mat_index=1)
        
    build_gullwing_lead_curved(bm, x_inner, x_outer, z_mid, width=3.00*0.001, thick=0.22*0.001, dir_sign=1.0, perp_pos=0.0, axis="x", mat_index=1)
    
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000005)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mats['ic_body'])
    obj.data.materials.append(mats['pin_tin'])
    return obj

def build_to252(name, mats):
    """Builds TO-252 (DPAK power transistor package)"""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    Lx = 6.10 * 0.001
    Ly = 6.60 * 0.001
    H = 2.30 * 0.001
    standoff = 0.10 * 0.001
    body_h = H - standoff
    
    add_box(bm, center=(0.0, 0.0, standoff + body_h / 2.0), size=(Lx, Ly, body_h), mat_index=0)
    
    # 2 Signal pins at -X
    x_inner = 3.05 * 0.001
    x_outer = 5.00 * 0.001
    z_mid = 0.60 * 0.001
    for y in [2.28, -2.28]:
        build_gullwing_lead_curved(bm, x_inner, x_outer, z_mid, width=0.80*0.001, thick=0.30*0.001, dir_sign=-1.0, perp_pos=y*0.001, axis="x", mat_index=1)
        
    # Large tab at +X
    tab_len = 1.60 * 0.001
    tab_w = 5.20 * 0.001
    tab_t = 0.50 * 0.001
    add_box(bm, center=(Lx/2 + tab_len/2, 0.0, tab_t / 2.0), size=(tab_len, tab_w, tab_t), mat_index=1)
    
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000005)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mats['ic_body'])
    obj.data.materials.append(mats['pin_tin'])
    return obj

def build_qfn32(name, mats):
    """Builds QFN-32 (5.0 x 5.0 mm, 0.5 mm pitch) quad flat no-leads package"""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    S = 5.00 * 0.001
    H = 0.90 * 0.001
    pad_len = 0.40 * 0.001
    pad_w = 0.25 * 0.001
    pad_t = 0.05 * 0.001
    
    # Molded plastic body (mat_index=0)
    add_box(bm, center=(0.0, 0.0, H / 2.0), size=(S, S, H), mat_index=0)
    
    # Large exposed thermal pad in center (mat_index=1)
    ep_size = 3.50 * 0.001
    add_box(bm, center=(0.0, 0.0, pad_t / 2.0), size=(ep_size, ep_size, pad_t), mat_index=1)
    
    # 8 peripheral contact pads per side
    pitch = 0.50 * 0.001
    offset_start = -3.5 * pitch
    
    for i in range(8):
        pos = offset_start + i * pitch
        add_box(bm, center=(-S/2 + pad_len/2, pos, pad_t / 2.0), size=(pad_len, pad_w, pad_t), mat_index=1)
        add_box(bm, center=(S/2 - pad_len/2, pos, pad_t / 2.0), size=(pad_len, pad_w, pad_t), mat_index=1)
        add_box(bm, center=(pos, -S/2 + pad_len/2, pad_t / 2.0), size=(pad_w, pad_len, pad_t), mat_index=1)
        add_box(bm, center=(pos, S/2 - pad_len/2, pad_t / 2.0), size=(pad_w, pad_len, pad_t), mat_index=1)
        
    # Pin 1 Dot Marker on top face at (-X, +Y)
    dot_radius = 0.30 * 0.001
    dot_x = -S/2 + 0.65 * 0.001
    dot_y = +S/2 - 0.65 * 0.001
    dot_z = H + 0.00001
    res = bmesh.ops.create_circle(bm, cap_ends=True, radius=dot_radius, segments=12)
    for v in res['verts']:
        v.co.x += dot_x
        v.co.y += dot_y
        v.co.z += dot_z
    for f in bm.faces:
        if all(v in res['verts'] for v in f.verts):
            f.material_index = 2
            
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000005)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mats['ic_body'])
    obj.data.materials.append(mats['pin_tin'])
    obj.data.materials.append(mats['marking_white'])
    return obj

def build_inductor_5050(name, mats):
    """
    Builds authentic Taiyo Yuden NR-50xx / SMD 5050 shielded power inductor (4.9 x 4.9 x 4.0 mm):
    - Signature octagonal ferrite body with 45° corner cutouts.
    - Recessed central magnetic core / winding waist.
    - Solder terminals wrapping around -X and +X sides.
    - Laser marking circular recess on top face.
    """
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    W = 4.90 * 0.001
    L = 4.90 * 0.001
    H = 4.00 * 0.001
    c = 0.85 * 0.001 # corner chamfer
    hw = W / 2.0
    hl = L / 2.0
    
    oct_pts = [
        (-hw + c, hl), (hw - c, hl),
        (hw, hl - c), (hw, -hl + c),
        (hw - c, -hl), (-hw + c, -hl),
        (-hw, -hl + c), (-hw, hl - c)
    ]
    
    # 1. Main Octagonal Ferrite Body (mat_index=0: ic_body)
    bot_verts = [bm.verts.new((x, y, 0.15 * 0.001)) for (x, y) in oct_pts]
    top_verts = [bm.verts.new((x, y, H)) for (x, y) in oct_pts]
    
    bm.faces.new(reversed(bot_verts)).material_index = 0
    bm.faces.new(top_verts).material_index = 0
    N = len(oct_pts)
    for i in range(N):
        next_i = (i + 1) % N
        bm.faces.new((bot_verts[i], bot_verts[next_i], top_verts[next_i], top_verts[i])).material_index = 0
        
    # 2. Top laser marking ring / circular depression (mat_index=2: marking_white)
    res_mark = bmesh.ops.create_circle(bm, cap_ends=True, radius=1.65*0.001, segments=24)
    for v in res_mark['verts']:
        v.co.z = H + 0.00002
    for f in bm.faces:
        if all(v in res_mark['verts'] for v in f.verts):
            f.material_index = 2
            
    # Central top dot marking
    res_dot = bmesh.ops.create_circle(bm, cap_ends=True, radius=0.40*0.001, segments=12)
    for v in res_dot['verts']:
        v.co.x = -1.0 * 0.001
        v.co.y = 1.0 * 0.001
        v.co.z = H + 0.00003
    for f in bm.faces:
        if all(v in res_dot['verts'] for v in f.verts):
            f.material_index = 2
            
    # 3. Solder Terminals wrapping around -X and +X (mat_index=1: pin_tin)
    pad_w = 1.30 * 0.001
    pad_l = 4.20 * 0.001
    pad_t = 0.20 * 0.001
    wrap_h = 1.20 * 0.001
    wrap_t = 0.12 * 0.001
    # -X pad (bottom + side wrap)
    add_box(bm, center=(-hw + pad_w/2.0, 0.0, pad_t/2.0), size=(pad_w, pad_l, pad_t), mat_index=1)
    add_box(bm, center=(-hw + wrap_t/2.0, 0.0, wrap_h/2.0), size=(wrap_t, pad_l, wrap_h), mat_index=1)
    # +X pad (bottom + side wrap)
    add_box(bm, center=(hw - pad_w/2.0, 0.0, pad_t/2.0), size=(pad_w, pad_l, pad_t), mat_index=1)
    add_box(bm, center=(hw - wrap_t/2.0, 0.0, wrap_h/2.0), size=(wrap_t, pad_l, wrap_h), mat_index=1)
    
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000005)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mats['ic_body'])
    obj.data.materials.append(mats['pin_tin'])
    obj.data.materials.append(mats['marking_white'])
    
    bev = obj.modifiers.new("Bevel", type='BEVEL')
    bev.width = 0.00015
    bev.segments = 2
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(40)
    return obj

def build_mesh_from_json(name, json_filename):
    """Loads mesh geometry from assets JSON if present"""
    import json
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, json_filename)
    if not os.path.exists(json_path):
        return None
    with open(json_path, 'r') as f:
        data = json.load(f)
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new((x * 0.001, y * 0.001, z * 0.001)) for (x, y, z) in data["verts"]]
    bm.verts.ensure_lookup_table()
    for face_info in data["faces"]:
        f_verts = [verts[idx] for idx in face_info["v"]]
        try:
            face = bm.faces.new(f_verts)
            face.material_index = face_info["mat"]
        except Exception:
            try:
                face = bm.faces.new(reversed(f_verts))
                face.material_index = face_info["mat"]
            except Exception:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000001)
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def build_potentiometer_ptv09a(name, mats):
    """
    Builds Bourns PTV09A-1 9mm vertical potentiometer:
    Uses the user-modified and perfected R33 pin/body geometry.
    """
    json_mesh = build_mesh_from_json(name, "r33_mesh.json")
    if json_mesh:
        obj = bpy.data.objects.new(name, json_mesh)
        obj.data.materials.append(mats['pot_blue'])
        obj.data.materials.append(mats['metal_shaft'])
        obj.data.materials.append(mats['pin_tin'])
        bev = obj.modifiers.new("Bevel", type='BEVEL')
        bev.width = 0.00015
        bev.segments = 2
        return obj

    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    # Body center exactly aligned with mounting tabs and shaft
    cx = 7.00 * 0.001
    cy = 2.50 * 0.001
    body_s = 9.50 * 0.001
    body_h = 7.00 * 0.001
    
    # 1. Main Housing (mat_index=0: Pot Blue)
    add_box(bm, center=(cx, cy, body_h / 2.0), size=(body_s, body_s, body_h), mat_index=0)
    
    # 2. Metal Mounting Frame / Bracket on bottom and sides (mat_index=2: Pin Tin)
    bracket_h = 2.20 * 0.001
    bracket_t = 0.50 * 0.001
    # Bottom plate
    add_box(bm, center=(cx, cy, bracket_t / 2.0), size=(body_s + 0.0002, body_s + 0.0002, bracket_t), mat_index=2)
    # Side brackets hugging -Y and +Y faces
    add_box(bm, center=(cx, cy - body_s/2.0 - bracket_t/2.0, bracket_h / 2.0), size=(body_s, bracket_t, bracket_h), mat_index=2)
    add_box(bm, center=(cx, cy + body_s/2.0 + bracket_t/2.0, bracket_h / 2.0), size=(body_s, bracket_t, bracket_h), mat_index=2)
    
    # 3. Threaded Bushing Collar at top of body (mat_index=1: Metal Shaft)
    collar_r = 3.25 * 0.001
    collar_h = 5.00 * 0.001
    hex_r = 3.80 * 0.001
    hex_h = 1.00 * 0.001
    res_hex = bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False,
        segments=6, radius1=hex_r, radius2=hex_r, depth=hex_h
    )
    for v in res_hex['verts']:
        v.co.x += cx
        v.co.y += cy
        v.co.z += body_h + hex_h / 2.0
    for f in bm.faces:
        if all(v in res_hex['verts'] for v in f.verts):
            f.material_index = 1
            
    res_collar = bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False,
        segments=24, radius1=collar_r, radius2=collar_r, depth=collar_h
    )
    for v in res_collar['verts']:
        v.co.x += cx
        v.co.y += cy
        v.co.z += body_h + hex_h + collar_h / 2.0
    for f in bm.faces:
        if all(v in res_collar['verts'] for v in f.verts):
            f.material_index = 1
            
    # 4. Metal D-Shaft with flat face (mat_index=1: Metal Shaft)
    shaft_r = 3.00 * 0.001
    shaft_h = 15.00 * 0.001
    res_shaft = bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False,
        segments=24, radius1=shaft_r, radius2=shaft_r, depth=shaft_h
    )
    for v in res_shaft['verts']:
        if v.co.x > 0.0015:
            v.co.x = 0.0015
        v.co.x += cx
        v.co.y += cy
        v.co.z += body_h + hex_h + collar_h + shaft_h / 2.0
    for f in bm.faces:
        if all(v in res_shaft['verts'] for v in f.verts):
            f.material_index = 1
            
    # 5. Signal Terminal Pins (3 separate parallel pins at X=0, Y=0.0, +2.5, +5.0 mm)
    pin_w = 0.80 * 0.001
    pin_t = 0.40 * 0.001
    pin_depth = 2.50 * 0.001
    body_front_x = cx - body_s / 2.0 # 2.25 mm
    
    for py in [0.0, 2.50, 5.00]:
        y_pin = py * 0.001
        add_box(bm, center=(body_front_x / 2.0, y_pin, pin_t / 2.0 + 0.0002), size=(body_front_x, pin_w, pin_t), mat_index=2)
        add_box(bm, center=(0.0, y_pin, -pin_depth / 2.0), size=(pin_w, pin_w, pin_depth), mat_index=2)
        
    # 6. Mounting Tabs at (+7.0, -1.9) and (+7.0, +6.9) mm going through PCB
    tab_w = 1.20 * 0.001
    tab_t = 0.60 * 0.001
    tab_depth = 2.80 * 0.001
    for my in [-1.90, 6.90]:
        add_box(bm, center=(cx, my * 0.001, -tab_depth / 2.0), size=(tab_w, tab_t, tab_depth), mat_index=2)
        
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000005)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mats['pot_blue'])
    obj.data.materials.append(mats['metal_shaft'])
    obj.data.materials.append(mats['pin_tin'])
    
    bev = obj.modifiers.new("Bevel", type='BEVEL')
    bev.width = 0.00015
    bev.segments = 2
    return obj

def build_slide_switch_sltv(name, mats):
    """
    Builds Würth WS-SLTV (10.0 x 2.5 x 6.4 mm) miniature THT slide switch:
    Uses the user-modified casing and slider geometry.
    """
    json_mesh = build_mesh_from_json(name, "sw1_mesh.json")
    if json_mesh:
        obj = bpy.data.objects.new(name, json_mesh)
        obj.data.materials.append(mats['pin_tin'])
        obj.data.materials.append(mats['ic_body'])
        bev = obj.modifiers.new("Bevel", type='BEVEL')
        bev.width = 0.00010
        bev.segments = 2
        return obj

    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    
    Lx = 10.00 * 0.001
    Ly = 2.50 * 0.001
    H = 6.40 * 0.001
    
    # 1. Metal casing (mat_index=0: pin_tin)
    add_box(bm, center=(0.0, 0.0, H / 2.0), size=(Lx, Ly, H), mat_index=0)
    
    # 2. Side mounting bracket tabs on ends (X = -5.0 and +5.0)
    ear_w = 1.20 * 0.001
    ear_h = 2.00 * 0.001
    add_box(bm, center=(-Lx/2 - ear_w/2, 0.0, ear_h / 2.0), size=(ear_w, Ly, ear_h), mat_index=0)
    add_box(bm, center=(+Lx/2 + ear_w/2, 0.0, ear_h / 2.0), size=(ear_w, Ly, ear_h), mat_index=0)
    
    # 3. 3 THT pins at X = -2.54, 0.0, +2.54, Y = 0.0 (mat_index=0: pin_tin)
    pin_w = 0.60 * 0.001
    pin_depth = 3.00 * 0.001
    for px in [-2.54, 0.0, 2.54]:
        add_box(bm, center=(px * 0.001, 0.0, -pin_depth / 2.0), size=(pin_w, pin_w, pin_depth), mat_index=0)
        
    # 4. Black Plastic Slide Actuator / Knob on top (mat_index=1: ic_body)
    knob_lx = 2.40 * 0.001
    knob_ly = 1.80 * 0.001
    knob_h = 3.60 * 0.001
    knob_x = -1.27 * 0.001 # in left position
    add_box(bm, center=(knob_x, 0.0, H + knob_h / 2.0), size=(knob_lx, knob_ly, knob_h), mat_index=1)
    
    # Grip ridges on knob top
    for rx in [-0.50, 0.0, 0.50]:
        add_box(bm, center=(knob_x + rx * 0.001, 0.0, H + knob_h + 0.0001), size=(0.20*0.001, knob_ly, 0.0002), mat_index=1)
        
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000005)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mats['pin_tin'])
    obj.data.materials.append(mats['ic_body'])
    
    bev = obj.modifiers.new("Bevel", type='BEVEL')
    bev.width = 0.00010
    bev.segments = 2
    return obj

def generate_footprints_library(target_blend_path):
    """
    Creates all standard packages with (0,0,0) local pivot,
    arranges them in collection, and saves target_blend_path.
    """
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.materials):
        if m.name.startswith("KiCad_"):
            bpy.data.materials.remove(m, do_unlink=True)
            
    mats = create_shared_materials()
    
    packages = [
        # SMD Resistors
        ("R_0402", build_smd_chip, {"length_mm": 1.00, "width_mm": 0.50, "height_mm": 0.35, "band_mm": 0.20, "is_resistor": True}),
        ("R_0603", build_smd_chip, {"length_mm": 1.60, "width_mm": 0.80, "height_mm": 0.45, "band_mm": 0.30, "is_resistor": True}),
        ("R_0805", build_smd_chip, {"length_mm": 2.00, "width_mm": 1.25, "height_mm": 0.55, "band_mm": 0.40, "is_resistor": True}),
        ("R_1206", build_smd_chip, {"length_mm": 3.20, "width_mm": 1.60, "height_mm": 0.60, "band_mm": 0.50, "is_resistor": True}),
        # SMD Capacitors
        ("C_0402", build_smd_chip, {"length_mm": 1.00, "width_mm": 0.50, "height_mm": 0.50, "band_mm": 0.20, "is_resistor": False}),
        ("C_0603", build_smd_chip, {"length_mm": 1.60, "width_mm": 0.80, "height_mm": 0.80, "band_mm": 0.30, "is_resistor": False}),
        ("C_0805", build_smd_chip, {"length_mm": 2.00, "width_mm": 1.25, "height_mm": 1.25, "band_mm": 0.40, "is_resistor": False}),
        ("C_1206", build_smd_chip, {"length_mm": 3.20, "width_mm": 1.60, "height_mm": 1.60, "band_mm": 0.50, "is_resistor": False}),
        # Transistors / Regulators
        ("SOT-23", build_sot23, {}),
        ("SOT-23-6", build_sot23_6, {}),
        ("SOT-223", build_sot223, {}),
        ("TO-252", build_to252, {}),
        # ICs
        ("SOIC-8", build_soic, {"num_pins": 8, "body_len_mm": 4.90, "body_wid_mm": 3.90, "total_wid_mm": 6.00, "height_mm": 1.45, "pitch_mm": 1.27}),
        ("TSSOP-8", build_tssop8, {}),
        ("SOIC-16", build_soic, {"num_pins": 16, "body_len_mm": 9.90, "body_wid_mm": 3.90, "total_wid_mm": 6.00, "height_mm": 1.45, "pitch_mm": 1.27}),
        ("QFN-32", build_qfn32, {}),
        # Inductors, Potentiometers & Switches
        ("IND_5050", build_inductor_5050, {}),
        ("POT_PTV09A", build_potentiometer_ptv09a, {}),
        ("SW_Slide_WS_SLTV", build_slide_switch_sltv, {}),
    ]
    
    col = bpy.data.collections.get("KiCad_Footprint_Library")
    if not col:
        col = bpy.data.collections.new("KiCad_Footprint_Library")
        bpy.context.scene.collection.children.link(col)
        
    created_objs = []
    for item in packages:
        name = item[0]
        func = item[1]
        kwargs = item[2]
        kwargs['mats'] = mats
        kwargs['name'] = name
        
        obj = func(**kwargs)
        col.objects.link(obj)
        obj.location = (0.0, 0.0, 0.0)
        created_objs.append(obj)
        try:
            obj.asset_mark()
        except:
            pass
            
    os.makedirs(os.path.dirname(target_blend_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=target_blend_path)
    print(f"Successfully generated {len(created_objs)} footprint packages in: {target_blend_path}")
    return created_objs

if __name__ == "__main__":
    target = "/home/a/KiCad Blender Add-on/kicad_pcb_tools/assets/footprints.blend"
    generate_footprints_library(target)
