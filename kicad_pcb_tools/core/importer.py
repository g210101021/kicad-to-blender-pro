import os
import bpy
import addon_utils
from . import cleaner
from . import transform_utils
from . import pcb_parser

def ensure_vrml_addon_enabled():
    """Checks and enables the VRML/X3D importer addon in Blender 4.2+ / 5.x"""
    addon_name = 'bl_ext.blender_org.web3d_x3d_vrml2_format'
    
    loaded_default, loaded_state = addon_utils.check(addon_name)
    if not loaded_state:
        try:
            addon_utils.enable(addon_name, default_set=True)
        except Exception as e:
            try:
                addon_utils.enable('io_scene_x3d', default_set=True)
            except Exception:
                raise RuntimeError(f"Could not enable VRML/X3D addon: {e}")
                
    if not hasattr(bpy.ops.import_scene, 'x3d'):
        raise RuntimeError("Operator bpy.ops.import_scene.x3d is not available!")

def import_kicad_wrl(filepath, pcb_filepath="", soldermask_preset='GREEN', use_pbr_materials=False, setup_studio=True):
    """
    Main import pipeline:
    1. Records existing scene objects so user models are NEVER affected.
    2. Imports VRML model.
    3. Isolates newly imported objects and separates board layers from component meshes.
    3b. Collapses duplicated VRML materials (guarded by shading equivalence).
    4. Categorizes PCB layers into Collections (keeping authentic original colors by default).
    5. In raw VRML space, spatially clusters and joins meshes into named components (e.g. C16_1uF, U5_RP2040).
    6. Rotates, centers, and scales the PCB (board + components) to real-life meters (factor 0.001).
    7. Sets layer origins to the board center (0, 0, 0).
    8. Applies micron-level physical Z offsets to board layers (Zero Z-Fighting!).
    9. Sets up 3-point soft studio lighting and hero camera.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
        
    ensure_vrml_addon_enabled()
    
    # 1. Record existing objects to guarantee isolation: existing user models are untouched!
    # Compare by name (set of ids is fine too, but names stay valid if a datablock is
    # replaced during import; this also avoids per-item RNA equality lookups later).
    existing_objs = set(o.name for o in bpy.data.objects)
    
    # 2. Run VRML import operator
    bpy.ops.import_scene.x3d(filepath=filepath)
    
    # 3. Isolate newly imported PCB objects
    new_objs = [o for o in bpy.data.objects if o.name not in existing_objs]
    if not new_objs:
        raise RuntimeError("No objects were imported from the VRML file!")
        
    board_objs = [o for o in new_objs if o.name.startswith("Shape_IndexedFaceSet")]
    comp_objs = [o for o in new_objs if not o.name.startswith("Shape_IndexedFaceSet")]

    # 3b. Collapse duplicated VRML materials onto their base datablock.
    # Runs BEFORE organize_into_collections so the stored kicad_orig_mat_name values
    # reference the surviving (base) materials, keeping "Restore Original File Colors"
    # valid. Scoped to imported objects only; the user's own materials are never touched.
    reassigned, purged = cleaner.deduplicate_component_materials(objects=new_objs)
    if reassigned:
        print(f"[KiCad Importer] Deduplicated materials: {reassigned} slot(s) "
              f"reassigned, {purged} orphan material(s) purged.")

    # 4. Organize collections (preserves original file colors unless use_pbr_materials is True)
    cleaner.organize_into_collections(
        pcb_new_objects=new_objs, 
        soldermask_preset=soldermask_preset, 
        use_pbr_materials=use_pbr_materials
    )
    
    # 5. Resolve kicad_pcb file: either user-specified, panel-selected, or auto-detected
    pcb_file = pcb_filepath.strip() if pcb_filepath else ""
    if not pcb_file:
        custom_pcb = getattr(bpy.context.scene, 'kicad_custom_pcb_path', '')
        if custom_pcb and os.path.exists(custom_pcb):
            pcb_file = custom_pcb
            
    if not pcb_file or not os.path.exists(pcb_file):
        pcb_file = pcb_parser.auto_detect_kicad_pcb(filepath)
        
    if pcb_file and os.path.exists(pcb_file):
        bpy.context.scene.kicad_custom_pcb_path = pcb_file
        
    # 6. In raw VRML space, match meshes to footprints, join each component, and classify
    joined_components = cleaner.name_and_classify_components(
        comp_objs=comp_objs,
        pcb_filepath=pcb_file
    )
    
    # 7. Combine all PCB objects (board layers + joined components)
    live_names = set(bpy.data.objects.keys())
    all_pcb_objects = [o for o in (board_objs + joined_components) if o.name in live_names]
    
    # 8. Rotate flat (-90 deg X), center at (0, 0, 0), and scale to real-life meters (0.001)
    transform_utils.center_and_orient_board(
        pcb_new_objects=all_pcb_objects, 
        scale_to_meters=True, 
        board_objects=board_objs,
        pcb_filepath=pcb_file
    )
    
    # 9. Apply physical Z offsets to eliminate Z-fighting
    cleaner.apply_layer_z_offsets()
    
    # 10. Setup studio lights & camera for real-scale PCB
    if setup_studio:
        transform_utils.setup_studio_lighting_and_camera()
        
    fp_count = 0
    if pcb_file and os.path.exists(pcb_file):
        footprints = pcb_parser.parse_kicad_pcb(pcb_file)
        fp_count = len(footprints)
        
    return {
        "status": "success",
        "total_objects": len(bpy.data.objects),
        "pcb_file": pcb_file,
        "pcb_components": len(joined_components)
    }

