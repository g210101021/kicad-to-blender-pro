import bpy
import os
from bpy.props import StringProperty, EnumProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper
from ..core import importer
from ..core import cleaner
from ..core import transform_utils
from ..core import material_engine
from ..core import footprint_placer
from ..core import material_harmony
from ..core import footprint_matcher

class KICAD_OT_import_board(bpy.types.Operator, ImportHelper):
    """Import KiCad VRML (.wrl) board, classify components, and make it production-ready"""
    bl_idname = "kicad.import_board"
    bl_label = "Import KiCad Board (.wrl)"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".wrl"
    filter_glob: StringProperty(
        default="*.wrl;*.vrml",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    pcb_filepath: StringProperty(
        name="KiCad PCB File",
        description="Optional path to .kicad_pcb file for component names and values (auto-detected if left empty)",
        default="",
        subtype='FILE_PATH'
    )
    
    use_pbr_materials: BoolProperty(
        name="Apply Custom PBR Shaders",
        description="Apply procedural PBR materials instead of original file colors (optional)",
        default=False
    )
    
    preset: EnumProperty(
        name="Solder Mask Color",
        description="Color preset for solder mask",
        items=[
            ('GREEN', "Classic Green", "Traditional KiCad green solder mask"),
            ('MATTE_BLACK', "Matte Black", "Modern stealth matte black"),
            ('GLOSSY_BLACK', "Glossy Black", "Sleek glossy piano black"),
            ('BLUE', "Royal Blue", "High-contrast royal blue"),
            ('PURPLE', "OSH Park Purple", "Signature purple mask with gold pads"),
            ('RED', "Ruby Red", "Vibrant dev board red"),
            ('WHITE', "Ceramic White", "Clean medical/automotive white"),
        ],
        default='GREEN'
    )
    
    setup_studio: BoolProperty(
        name="Setup Studio Lighting & Camera",
        description="Automatically adds 3-point soft studio lights and framed hero camera",
        default=True
    )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_pbr_materials")
        if self.use_pbr_materials:
            layout.prop(self, "preset")
        layout.prop(self, "setup_studio")
        
        box = layout.box()
        box.label(text="Component Metadata (.kicad_pcb)", icon='TEXT')
        box.prop(self, "pcb_filepath", text="PCB File")
    
    def execute(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "No VRML file specified!")
            return {'CANCELLED'}
            
        try:
            res = importer.import_kicad_wrl(
                filepath=self.filepath,
                pcb_filepath=self.pcb_filepath,
                soldermask_preset=self.preset,
                use_pbr_materials=self.use_pbr_materials,
                setup_studio=self.setup_studio
            )
            msg = f"KiCad Board imported successfully! ({res['total_objects']} objects)"
            if res.get('pcb_components'):
                pcb_name = os.path.basename(res['pcb_file'])
                msg += f" [Linked {res['pcb_components']} components from {pcb_name}]"
            self.report({'INFO'}, msg)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            return {'CANCELLED'}

class KICAD_OT_select_kicad_pcb(bpy.types.Operator, ImportHelper):
    """Select KiCad PCB (.kicad_pcb) file directly to link component names and properties"""
    bl_idname = "kicad.select_pcb_file"
    bl_label = "Select .kicad_pcb File"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".kicad_pcb"
    filter_glob: StringProperty(
        default="*.kicad_pcb",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    def execute(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "No .kicad_pcb file specified!")
            return {'CANCELLED'}
            
        context.scene.kicad_custom_pcb_path = self.filepath
        self.report({'INFO'}, f"Selected KiCad PCB: {os.path.basename(self.filepath)}")
        return {'FINISHED'}

class KICAD_OT_change_soldermask_color(bpy.types.Operator):
    """Change the solder mask color preset on existing imported PCB"""
    bl_idname = "kicad.change_soldermask"
    bl_label = "Apply Solder Mask Color"
    bl_options = {'REGISTER', 'UNDO'}
    
    preset: EnumProperty(
        name="Color",
        items=[
            ('GREEN', "Classic Green", ""),
            ('MATTE_BLACK', "Matte Black", ""),
            ('GLOSSY_BLACK', "Glossy Black", ""),
            ('BLUE', "Royal Blue", ""),
            ('PURPLE', "OSH Park Purple", ""),
            ('RED', "Ruby Red", ""),
            ('WHITE', "Ceramic White", ""),
        ],
        default='GREEN'
    )
    
    def execute(self, context):
        new_mat = material_engine.setup_soldermask_material(self.preset)
        applied_count = 0
        for obj in bpy.data.objects:
            if obj.name.startswith("PCB_SolderMask") or "SolderMask" in obj.name:
                if obj.data.materials:
                    obj.data.materials[0] = new_mat
                    applied_count += 1
                else:
                    obj.data.materials.append(new_mat)
                    applied_count += 1
        self.report({'INFO'}, f"Updated solder mask to {self.preset} on {applied_count} objects.")
        return {'FINISHED'}

class KICAD_OT_apply_pbr_materials(bpy.types.Operator):
    """Apply photorealistic procedural PBR shaders to all board layers"""
    bl_idname = "kicad.apply_pbr_materials"
    bl_label = "Apply PBR Shaders"
    bl_options = {'REGISTER', 'UNDO'}
    
    preset: EnumProperty(
        name="Solder Mask Color",
        items=[
            ('GREEN', "Classic Green", ""),
            ('MATTE_BLACK', "Matte Black", ""),
            ('GLOSSY_BLACK', "Glossy Black", ""),
            ('BLUE', "Royal Blue", ""),
            ('PURPLE', "OSH Park Purple", ""),
            ('RED', "Ruby Red", ""),
            ('WHITE', "Ceramic White", ""),
        ],
        default='GREEN'
    )
    
    def execute(self, context):
        applied = cleaner.apply_pbr_materials_to_board(self.preset)
        self.report({'INFO'}, f"Applied procedural PBR materials to {applied} board layers.")
        return {'FINISHED'}

class KICAD_OT_restore_original_colors(bpy.types.Operator):
    """Restore original VRML materials and colors directly from the KiCad file"""
    bl_idname = "kicad.restore_original_colors"
    bl_label = "Restore Original File Colors"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        restored = cleaner.restore_original_board_materials()
        self.report({'INFO'}, f"Restored original file colors on {restored} board layers.")
        return {'FINISHED'}

class KICAD_OT_recenter_board(bpy.types.Operator):
    """Recenter board objects to the world origin (0, 0, 0) without changing scale"""
    bl_idname = "kicad.recenter_board"
    bl_label = "Recenter PCB to Origin"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        transform_utils.recenter_board_to_origin()
        cleaner.apply_layer_z_offsets()
        self.report({'INFO'}, "PCB centered to origin and Z-offsets refreshed.")
        return {'FINISHED'}

class KICAD_OT_setup_studio(bpy.types.Operator):
    """Add professional 3-point soft studio lighting and framed camera"""
    bl_idname = "kicad.setup_studio"
    bl_label = "Add Studio Lights & Camera"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        transform_utils.setup_studio_lighting_and_camera()
        self.report({'INFO'}, "Studio lighting and camera created.")
        return {'FINISHED'}

PACKAGE_ITEMS = [
    ("R_0402", "R_0402 (Resistor)", "SMD 0402 Resistor (1.00 x 0.50 x 0.35 mm)"),
    ("R_0603", "R_0603 (Resistor)", "SMD 0603 Resistor (1.60 x 0.80 x 0.45 mm)"),
    ("R_0805", "R_0805 (Resistor)", "SMD 0805 Resistor (2.00 x 1.25 x 0.55 mm)"),
    ("R_1206", "R_1206 (Resistor)", "SMD 1206 Resistor (3.20 x 1.60 x 0.60 mm)"),
    ("C_0402", "C_0402 (Capacitor)", "SMD 0402 MLCC Capacitor (1.00 x 0.50 x 0.50 mm)"),
    ("C_0603", "C_0603 (Capacitor)", "SMD 0603 MLCC Capacitor (1.60 x 0.80 x 0.80 mm)"),
    ("C_0805", "C_0805 (Capacitor)", "SMD 0805 MLCC Capacitor (2.00 x 1.25 x 1.25 mm)"),
    ("C_1206", "C_1206 (Capacitor)", "SMD 1206 MLCC Capacitor (3.20 x 1.60 x 1.60 mm)"),
    ("SOT-23", "SOT-23 (3-Pin Transistor)", "SOT-23 3-Pin Small Outline Transistor"),
    ("SOT-23-6", "SOT-23-6 (6-Pin IC)", "SOT-23-6 / SOT-23-6L (6-Pin, 0.95mm pitch) IC"),
    ("SOT-223", "SOT-223 (Regulator)", "SOT-223 4-Pin / Tab Voltage Regulator"),
    ("TO-252", "TO-252 (DPAK)", "TO-252 / DPAK Power Transistor / Diode Package"),
    ("SOIC-8", "SOIC-8 (1.27mm pitch)", "SOIC-8 (8-Pin, 1.27mm pitch) IC"),
    ("TSSOP-8", "TSSOP-8 (0.65mm pitch)", "TSSOP-8 / SOP-8 (8-Pin, 0.65mm pitch) IC (FS8205A)"),
    ("SOIC-16", "SOIC-16 / SOP-16", "SOIC-16 (16-Pin, 1.27mm pitch) IC"),
    ("QFN-32", "QFN-32 (5x5mm)", "QFN-32 (5.0 x 5.0 mm, 0.5mm pitch) Leadless IC"),
    ("IND_5050", "IND_5050 (Power Inductor)", "SMD 5050 Shielded Power Inductor (5x5mm)"),
    ("POT_PTV09A", "POT_PTV09A (Potentiometer)", "Bourns PTV09A 9mm Vertical Potentiometer with Shaft"),
    ("SW_Slide_WS_SLTV", "SW_Slide (Slide Switch)", "Würth WS-SLTV 3-Pin Miniature THT Slide Switch"),
]

class KiCadMissingComponentItem(bpy.types.PropertyGroup):
    ref: StringProperty(name="Reference")
    val: StringProperty(name="Value")
    fp_name: StringProperty(name="Footprint")
    layer: StringProperty(name="Layer", default="F.Cu")
    pos_x: bpy.props.FloatProperty(name="X")
    pos_y: bpy.props.FloatProperty(name="Y")
    rot_z: bpy.props.FloatProperty(name="Rotation")
    suggested_package: StringProperty(name="Suggested Package")
    selected_package: EnumProperty(
        name="Package",
        items=PACKAGE_ITEMS,
        default='SOIC-8'
    )

class KICAD_OT_scan_missing_components(bpy.types.Operator):
    """Scan PCB for missing 3D components and auto-match against the built-in library"""
    bl_idname = "kicad.scan_missing_components"
    bl_label = "Scan Missing Components"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scan_res = footprint_placer.scan_missing_components()
        if "error" in scan_res:
            self.report({'ERROR'}, scan_res["error"])
            return {'CANCELLED'}
            
        scene = context.scene
        scene.kicad_missing_components.clear()
        
        for item in scan_res.get("missing_list", []):
            entry = scene.kicad_missing_components.add()
            entry.ref = item["ref"]
            entry.val = item["val"]
            entry.fp_name = item["fp_name"]
            entry.layer = item.get("layer", "F.Cu")
            entry.pos_x = item["pos_x"]
            entry.pos_y = item["pos_y"]
            entry.rot_z = item["rot_z"]
            entry.suggested_package = item["suggested_package"] or ""
            if item["suggested_package"] in [p[0] for p in PACKAGE_ITEMS]:
                entry.selected_package = item["suggested_package"]
            else:
                entry.selected_package = 'SOIC-8'
                
        scene.kicad_missing_count = scan_res["missing_count"]
        scene.kicad_matched_count = scan_res["matched_count"]
        
        msg = f"Found {scan_res['missing_count']} missing components ({scan_res['matched_count']} auto-matchable)."
        self.report({'INFO'}, msg)
        return {'FINISHED'}

class KICAD_OT_fill_auto_matched(bpy.types.Operator):
    """Place all auto-matched components into the scene with consistent shading"""
    bl_idname = "kicad.fill_auto_matched"
    bl_label = "Fill Auto-Matched Components"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            count, placed = footprint_placer.fill_all_matched_components()
            bpy.ops.kicad.scan_missing_components()
            self.report({'INFO'}, f"Successfully placed {count} library components on the PCB.")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to fill matched components: {e}")
            return {'CANCELLED'}

class KICAD_OT_place_single_missing(bpy.types.Operator):
    """Place a single missing component using the selected package"""
    bl_idname = "kicad.place_single_missing"
    bl_label = "Place Component"
    bl_options = {'REGISTER', 'UNDO'}
    
    ref: StringProperty(name="Reference", default="")
    
    def execute(self, context):
        scene = context.scene
        target_item = None
        for item in scene.kicad_missing_components:
            if item.ref == self.ref:
                target_item = item
                break
                
        if not target_item:
            self.report({'ERROR'}, f"Component {self.ref} not found in missing list!")
            return {'CANCELLED'}
            
        comp_data = {
            "ref": target_item.ref,
            "val": target_item.val,
            "fp_name": target_item.fp_name,
            "layer": target_item.layer,
            "pos_x": target_item.pos_x,
            "pos_y": target_item.pos_y,
            "rot_z": target_item.rot_z,
            "suggested_package": target_item.suggested_package
        }
        
        try:
            obj = footprint_placer.place_component(comp_data, package_name=target_item.selected_package)
            bpy.ops.kicad.scan_missing_components()
            self.report({'INFO'}, f"Placed {obj.name} as {target_item.selected_package}.")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Placement failed: {e}")
            return {'CANCELLED'}

class KICAD_OT_harmonize_materials(bpy.types.Operator):
    """Harmonize and unify shaders across all components for 100% material consistency"""
    bl_idname = "kicad.harmonize_materials"
    bl_label = "Harmonize Component Shaders"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        count = material_harmony.harmonize_all_components()
        self.report({'INFO'}, f"Unified {count} component material slots to master PBR shaders.")
        return {'FINISHED'}

class KICAD_UL_missing_components(bpy.types.UIList):
    """Custom UIList for missing components"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            col_ref = row.column()
            col_ref.scale_x = 0.8
            if item.suggested_package:
                col_ref.label(text=item.ref, icon='CHECKMARK')
                row.label(text=f"{item.val}" if item.val else "")
                row.label(text=f"-> {item.suggested_package}")
            else:
                col_ref.label(text=item.ref, icon='QUESTION')
                row.label(text=f"{item.val}" if item.val else "")
                row.prop(item, "selected_package", text="")
                
            op = row.operator("kicad.place_single_missing", text="", icon='FORWARD')
            op.ref = item.ref
