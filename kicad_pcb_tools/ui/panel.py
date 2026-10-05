import bpy
import os

class KICAD_PT_main_panel(bpy.types.Panel):
    """Main Sidebar Panel for KiCad PCB Tools in 3D Viewport"""
    bl_label = "KiCad PCB Tools"
    bl_idname = "KICAD_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'KiCad PCB'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 1. Quick Import & Setup
        box = layout.box()
        box.label(text="Import & Processing", icon='IMPORT')
        
        row = box.row()
        row.scale_y = 1.5
        row.operator("kicad.import_board", text="Import KiCad .WRL Board", icon='FILE_3D')
        
        # PCB Metadata file selection
        pcb_box = box.box()
        pcb_box.label(text="Component Metadata (.kicad_pcb)", icon='TEXT')
        custom_pcb = getattr(scene, 'kicad_custom_pcb_path', '')
        if custom_pcb and os.path.exists(custom_pcb):
            pcb_box.label(text=f"Selected: {os.path.basename(custom_pcb)}", icon='CHECKMARK')
        else:
            pcb_box.label(text="Auto-detected if in same folder", icon='INFO')
        pcb_box.operator("kicad.select_pcb_file", text="Select .kicad_pcb Manually", icon='FILE_FOLDER')
        
        # Real-World Dimension Info Box
        sub = bpy.data.objects.get("PCB_Substrate_FR4")
        if sub:
            info_box = box.box()
            info_box.label(text=f"PCB Size: {sub.dimensions.x * 1000:.1f} × {sub.dimensions.y * 1000:.1f} × {sub.dimensions.z * 1000:.2f} mm", icon='INFO')
        
        # 2. Material & Solder Mask Customization (Optional)
        box = layout.box()
        box.label(text="Colors & Materials (Optional)", icon='MATERIAL')
        
        col = box.column(align=True)
        col.label(text="Solder Mask Color Presets:")
        grid = col.grid_flow(columns=2, align=True)
        props = grid.operator("kicad.change_soldermask", text="Classic Green", icon='COLORSET_03_VEC')
        props.preset = 'GREEN'
        
        props = grid.operator("kicad.change_soldermask", text="Matte Black", icon='COLORSET_01_VEC')
        props.preset = 'MATTE_BLACK'
        
        props = grid.operator("kicad.change_soldermask", text="Glossy Black", icon='COLORSET_01_VEC')
        props.preset = 'GLOSSY_BLACK'
        
        props = grid.operator("kicad.change_soldermask", text="Royal Blue", icon='COLORSET_04_VEC')
        props.preset = 'BLUE'
        
        props = grid.operator("kicad.change_soldermask", text="OSH Purple", icon='COLORSET_06_VEC')
        props.preset = 'PURPLE'
        
        props = grid.operator("kicad.change_soldermask", text="Ruby Red", icon='COLORSET_02_VEC')
        props.preset = 'RED'
        
        props = grid.operator("kicad.change_soldermask", text="Ceramic White", icon='COLORSET_09_VEC')
        props.preset = 'WHITE'
        
        box.separator()
        row = box.row(align=True)
        row.operator("kicad.apply_pbr_materials", text="Apply PBR Shaders", icon='SHADING_RENDERED')
        row.operator("kicad.restore_original_colors", text="Restore File Colors", icon='FILE_REFRESH')
        
        # 3. Missing Components & Built-in Library
        box = layout.box()
        box.label(text="Missing Components & Library", icon='PACKAGE')
        
        missing_count = getattr(scene, 'kicad_missing_count', 0)
        matched_count = getattr(scene, 'kicad_matched_count', 0)
        has_items = len(getattr(scene, 'kicad_missing_components', [])) > 0
        
        row = box.row(align=True)
        row.scale_y = 1.2
        row.operator("kicad.scan_missing_components", text="Scan Missing Components", icon='VIEWZOOM')
        
        if has_items:
            info_col = box.column(align=True)
            info_col.label(text=f"Missing: {missing_count} | Auto-Matched: {matched_count}", icon='INFO')
            
            if matched_count > 0:
                row_fill = box.row()
                row_fill.scale_y = 1.3
                row_fill.operator("kicad.fill_auto_matched", text=f"Fill Auto-Matched ({matched_count} Parts)", icon='AUTOMERGE')
                
            box.label(text="Missing Parts (Manual Assignment):")
            box.template_list(
                "KICAD_UL_missing_components", "",
                scene, "kicad_missing_components",
                scene, "kicad_missing_active_index",
                rows=3, maxrows=6
            )
            
        box.separator()
        row_harm = box.row()
        row_harm.operator("kicad.harmonize_materials", text="Harmonize Component Shaders", icon='MATERIAL_DATA')
        
        # 4. Scene & Transformation Utilities
        box = layout.box()
        box.label(text="Scene Utilities", icon='TOOL_SETTINGS')
        col = box.column(align=True)
        col.operator("kicad.recenter_board", text="Recenter PCB to Origin", icon='OBJECT_ORIGIN')
        col.operator("kicad.setup_studio", text="Rebuild Studio Lighting & Cam", icon='LIGHT_AREA')
