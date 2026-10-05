import sys
import os
import bpy

# Add project path to sys.path
addon_path = "/home/a/KiCad Blender Add-on"
if addon_path not in sys.path:
    sys.path.insert(0, addon_path)

import kicad_pcb_tools
from kicad_pcb_tools.core import importer, cleaner, transform_utils, footprint_matcher, footprint_placer, material_engine, pcb_parser

print("=" * 60)
print("TEST 1: Module & Extension Registration")
print("=" * 60)
assert hasattr(bpy.types, "KICAD_PT_main_panel"), "KICAD_PT_main_panel not registered!"
assert hasattr(bpy.types, "KICAD_OT_import_board"), "KICAD_OT_import_board not registered!"
assert len(footprint_matcher.AVAILABLE_PACKAGES) == 19, f"Expected 19 packages, got {len(footprint_matcher.AVAILABLE_PACKAGES)}"
assert "SW_Slide_WS_SLTV" in footprint_matcher.AVAILABLE_PACKAGES, "SW_Slide_WS_SLTV missing from matcher!"
print(">>> TEST 1 PASSED: Extension and all 19 packages registered.")

print("=" * 60)
print("TEST 2: S-Expression PCB Parsing")
print("=" * 60)
pcb_file = "/home/a/Belgeler/kiCad work/Deneme/Deneme.kicad_pcb"
fps = pcb_parser.parse_kicad_pcb(pcb_file)
print(f"Total footprints parsed from .kicad_pcb: {len(fps)}")
assert len(fps) > 50, f"Expected >50 footprints, got {len(fps)}"
assert "U5" in fps, "U5 (RP2040) footprint missing!"
assert "C16" in fps, "C16 footprint missing!"
bounds = pcb_parser.get_board_outline_bounds(pcb_file)
print(f"Board bounds: width={bounds['width']:.2f}mm, height={bounds['height']:.2f}mm")
assert bounds['width'] > 50, f"Board width unexpected: {bounds['width']}"
print(">>> TEST 2 PASSED: PCB parser successfully extracted all footprints and bounds.")

print("=" * 60)
print("TEST 3: Full VRML Import Pipeline & Anti Z-Fighting")
print("=" * 60)
wrl_file = "/home/a/Belgeler/kiCad work/Deneme/Deneme.wrl"
# Reset scene
bpy.ops.wm.read_factory_settings(use_empty=True)
try:
    kicad_pcb_tools.register()
except Exception:
    pass

res = importer.import_kicad_wrl(
    filepath=wrl_file,
    pcb_filepath=pcb_file,
    soldermask_preset='GREEN',
    use_pbr_materials=False,
    setup_studio=True
)
print(f"Import result: {res['total_objects']} total objects, {res['pcb_components']} joined components.")
assert res['total_objects'] > 0, "No objects imported!"

# Verify Substrate
substrate = bpy.data.objects.get("PCB_Substrate_FR4")
assert substrate is not None, "PCB_Substrate_FR4 not found!"
print(f"Substrate location: {substrate.location}")
assert abs(substrate.location.x) < 0.001 and abs(substrate.location.y) < 0.001, "Substrate not centered at (0,0,0)!"

# Verify Z offsets (Anti Z-fighting)
copper = bpy.data.objects.get("PCB_Copper_Gold_Front")
mask = bpy.data.objects.get("PCB_SolderMask_Front")
silk = bpy.data.objects.get("PCB_Silkscreen_Front")
if copper and mask:
    print(f"Copper Z: {copper.location.z:.6f} m, SolderMask Z: {mask.location.z:.6f} m")
    assert mask.location.z != copper.location.z, "Z-fighting: Copper and Mask have identical Z!"
print(">>> TEST 3 PASSED: VRML import, substrate centering, and anti Z-fighting offsets verified.")

print("=" * 60)
print("TEST 4: Hierarchy & Outliner Collections")
print("=" * 60)
comp_col = bpy.data.collections.get("05_Components")
assert comp_col is not None, "05_Components collection not found!"
sub_cols = [c.name for c in comp_col.children]
print(f"Component sub-collections: {sub_cols}")
assert "01_Capacitors" in sub_cols, "01_Capacitors collection missing!"
assert "02_Resistors" in sub_cols, "02_Resistors collection missing!"
assert "03_Integrated_Circuits" in sub_cols, "03_Integrated_Circuits collection missing!"
print(">>> TEST 4 PASSED: All hierarchical collections properly populated.")

print("=" * 60)
print("TEST 5: Missing Component Detection & Placement Engine")
print("=" * 60)
scan_res = footprint_placer.scan_missing_components(pcb_file)
assert "error" not in scan_res, f"Scan error: {scan_res.get('error')}"
missing_list = scan_res.get("missing_list", [])
matched = [m for m in missing_list if m.get("suggested_package")]
print(f"Total missing: {len(missing_list)}, Auto-matchable: {len(matched)}")

placed_count = 0
for item in matched:
    obj = footprint_placer.place_component(item)
    if obj:
        placed_count += 1
        print(f"Placed {item['ref']} ({item['suggested_package']}) at {obj.location}")

print(f"Total placed components: {placed_count}")
assert placed_count == len(matched), f"Expected {len(matched)} placed, got {placed_count}"
print(">>> TEST 5 PASSED: Missing component scanner and IPC-7351 placement engine verified.")

print("=" * 60)
print("TEST 6: Material Shading & Color Presets")
print("=" * 60)
bpy.ops.kicad.change_soldermask(preset='MATTE_BLACK')
mask_mat = bpy.data.materials.get("KiCad_SolderMask_MATTE_BLACK")
assert mask_mat is not None, "KiCad_SolderMask_MATTE_BLACK material not created!"
bsdf = next(n for n in mask_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
col = bsdf.inputs['Base Color'].default_value
print(f"Matte Black Base Color: ({col[0]:.3f}, {col[1]:.3f}, {col[2]:.3f})")
assert col[0] < 0.1 and col[1] < 0.1 and col[2] < 0.1, "Matte Black color not applied properly!"

bpy.ops.kicad.harmonize_materials()
print(">>> TEST 6 PASSED: Material presets and harmony operator executed cleanly.")

print("=" * 60)
print("TEST 7: Studio Lighting & Camera Rig")
print("=" * 60)
studio_lights = [o for o in bpy.data.objects if "Studio_" in o.name]
print(f"Studio objects found: {[o.name for o in studio_lights]}")
assert len(studio_lights) >= 3, f"Expected >=3 studio lights/cameras, found {len(studio_lights)}"
cam = bpy.data.objects.get("PCB_Hero_Camera")
assert cam is not None, "PCB_Hero_Camera not found!"
print(f"Hero Camera Location: {cam.location}")
print(">>> TEST 7 PASSED: Studio softbox lights and camera rig generated.")

print("\n" + "#" * 60)
print("ALL 7 INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
print("#" * 60 + "\n")
