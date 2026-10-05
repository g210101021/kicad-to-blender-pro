bl_info = {
    "name": "KiCad to Blender Pro",
    "author": "Veysel TURAN",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > KiCad PCB",
    "description": "Imports KiCad VRML models, organizes hierarchy, optimizes meshes, applies PBR materials and studio lighting.",
    "category": "Import-Export",
}

import bpy
from bpy.props import StringProperty, IntProperty, CollectionProperty
from .ui import operators
from .ui import panel

classes = (
    operators.KiCadMissingComponentItem,
    operators.KICAD_OT_import_board,
    operators.KICAD_OT_select_kicad_pcb,
    operators.KICAD_OT_change_soldermask_color,
    operators.KICAD_OT_apply_pbr_materials,
    operators.KICAD_OT_restore_original_colors,
    operators.KICAD_OT_recenter_board,
    operators.KICAD_OT_setup_studio,
    operators.KICAD_OT_scan_missing_components,
    operators.KICAD_OT_fill_auto_matched,
    operators.KICAD_OT_place_single_missing,
    operators.KICAD_OT_harmonize_materials,
    operators.KICAD_UL_missing_components,
    panel.KICAD_PT_main_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.kicad_custom_pcb_path = StringProperty(
        name="Custom PCB Path",
        description="Path to user selected .kicad_pcb file",
        default=""
    )
    bpy.types.Scene.kicad_missing_components = CollectionProperty(
        type=operators.KiCadMissingComponentItem
    )
    bpy.types.Scene.kicad_missing_active_index = IntProperty(default=0)
    bpy.types.Scene.kicad_missing_count = IntProperty(default=0)
    bpy.types.Scene.kicad_matched_count = IntProperty(default=0)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    for prop in ["kicad_custom_pcb_path", "kicad_missing_components", "kicad_missing_active_index", "kicad_missing_count", "kicad_matched_count"]:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)

if __name__ == "__main__":
    register()
