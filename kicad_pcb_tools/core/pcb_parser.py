import os
import re
import math

def parse_kicad_pcb(pcb_path):
    """
    Parses a .kicad_pcb file and extracts all footprints with their
    Reference (e.g. C16, R8, U1), Value, Footprint name, Coordinates,
    Layer (F.Cu or B.Cu), and 3D Model file.
    """
    if not pcb_path or not os.path.exists(pcb_path):
        return {}
        
    with open(pcb_path, 'r', errors='ignore') as f:
        text = f.read()
        
    footprints = {}
    fp_matches = list(re.finditer(r'\(footprint\s+\"([^\"]+)\"', text))
    
    for i in range(len(fp_matches)):
        start = fp_matches[i].start()
        if i + 1 < len(fp_matches):
            end = fp_matches[i+1].start()
        else:
            depth = 0
            end = len(text)
            for idx in range(start, len(text)):
                ch = text[idx]
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        end = idx + 1
                        break
        block = text[start:end]
        
        fp_name = fp_matches[i].group(1)
        ref_match = re.search(r'\(property\s+\"Reference\"\s+\"([^\"]+)\"', block)
        val_match = re.search(r'\(property\s+\"Value\"\s+\"([^\"]+)\"', block)
        layer_match = re.search(r'\(layer\s+\"([^\"]+)\"\)', block)
        at_match = re.search(r'\(at\s+([^\)]+)\)', block)
        model_match = re.search(r'\(model\s+\"([^\"]+)\"', block)
        
        ref = ref_match.group(1) if ref_match else f"FP_{i}"
        val = val_match.group(1) if val_match else ""
        layer = layer_match.group(1) if layer_match else "F.Cu"
        
        at_parts = at_match.group(1).split() if at_match else ["0", "0"]
        pos_x = float(at_parts[0]) if len(at_parts) > 0 else 0.0
        pos_y = float(at_parts[1]) if len(at_parts) > 1 else 0.0
        rot_z = float(at_parts[2]) if len(at_parts) > 2 else 0.0
        
        model_name = os.path.basename(model_match.group(1)) if model_match else ""
        
        footprints[ref] = {
            "ref": ref,
            "val": val,
            "fp_name": fp_name,
            "layer": layer,
            "pos_x": pos_x,
            "pos_y": pos_y,
            "rot_z": rot_z,
            "model_name": model_name
        }
        
    return footprints

def get_board_outline_bounds(pcb_path):
    """
    Board outline in KiCad mm space.

    Prefers the true Edge.Cuts geometry. Falls back to the union of all footprint
    courtyards only when no Edge.Cuts elements exist (rare, but keeps the function
    useful instead of returning None).
    """
    bounds = get_edge_cuts_bounds(pcb_path)
    if bounds:
        return bounds

    fps = parse_kicad_pcb(pcb_path)
    if not fps:
        return None

    xs = [d['pos_x'] for d in fps.values()]
    ys = [d['pos_y'] for d in fps.values()]
    return {
        "min_x": min(xs), "max_x": max(xs),
        "min_y": min(ys), "max_y": max(ys),
        "center_x": (min(xs) + max(xs)) / 2.0,
        "center_y": (min(ys) + max(ys)) / 2.0,
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
    }


def get_edge_cuts_bounds(pcb_path):
    """
    Parses Edge.Cuts elements in .kicad_pcb to calculate the PCB bounding box
    and center coordinates in KiCad mm space.
    """
    if not pcb_path or not os.path.exists(pcb_path):
        return None
        
    with open(pcb_path, 'r', errors='ignore') as f:
        text = f.read()
        
    # Collect Edge.Cuts geometry. `gr_arc` is handled specially: its start/end are
    # points ON the circle, so they understate the true extent. We use the centre
    # plus radius to get the full bounding box of the arc's bounding circle.
    edge_blocks = re.findall(r'\(gr_\w+\s+.*?\blayer\s+\"Edge\.Cuts\".*?\)', text, re.DOTALL)

    xs = []
    ys = []
    coord_pattern = re.compile(r'\((?:start|end|mid|center|xy)\s+([-\d.]+)\s+([-\d.]+)\)')

    for block in edge_blocks:
        is_arc = block.lstrip().startswith('(gr_arc')
        if is_arc:
            s = re.search(r'\(start\s+([-\d.]+)\s+([-\d.]+)\)', block)
            m = re.search(r'\(mid\s+([-\d.]+)\s+([-\d.]+)\)', block)
            e = re.search(r'\(end\s+([-\d.]+)\s+([-\d.]+)\)', block)
            c = re.search(r'\(center\s+([-\d.]+)\s+([-\d.]+)\)', block)
            if s and m and e:
                try:
                    sx, sy = float(s.group(1)), float(s.group(2))
                    mx, my = float(m.group(1)), float(m.group(2))
                    ex, ey = float(e.group(1)), float(e.group(2))
                    if c:
                        cx, cy = float(c.group(1)), float(c.group(2))
                    else:
                        # KiCad 6+ stores arcs as start/mid/end. Recover the centre as
                        # the circumcentre of the three points.
                        d = 2.0 * (sx * (my - ey) + mx * (ey - sy) + ex * (sy - my))
                        if abs(d) < 1e-12:
                            raise ValueError("degenerate arc")
                        a_sq = sx * sx + sy * sy
                        m_sq = mx * mx + my * my
                        e_sq = ex * ex + ey * ey
                        cx = (a_sq * (my - ey) + m_sq * (ey - sy) + e_sq * (sy - my)) / d
                        cy = (a_sq * (ex - mx) + m_sq * (sx - ex) + e_sq * (mx - sx)) / d
                    r = max(math.hypot(sx - cx, sy - cy), math.hypot(ex - cx, ey - cy))
                    # Conservative: full bounding circle of the arc.
                    xs.extend([cx - r, cx + r])
                    ys.extend([cy - r, cy + r])
                    continue
                except ValueError:
                    pass
        for m in coord_pattern.finditer(block):
            try:
                xs.append(float(m.group(1)))
                ys.append(float(m.group(2)))
            except ValueError:
                pass

    if not xs or not ys:
        return None
        
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    return {
        "min_x": min_x,
        "max_x": max_x,
        "min_y": min_y,
        "max_y": max_y,
        "center_x": (min_x + max_x) / 2.0,
        "center_y": (min_y + max_y) / 2.0,
        "width": max_x - min_x,
        "height": max_y - min_y
    }

def auto_detect_kicad_pcb(wrl_filepath):
    """
    Tries to automatically find a .kicad_pcb file:
    1. Same base name: filename.kicad_pcb
    2. Any .kicad_pcb file in the same folder
    3. Any .kicad_pcb file in parent directory
    """
    if not wrl_filepath:
        return ""
        
    base, _ = os.path.splitext(wrl_filepath)
    candidate = base + ".kicad_pcb"
    if os.path.exists(candidate):
        return candidate
        
    dir_path = os.path.dirname(wrl_filepath)
    if os.path.isdir(dir_path):
        for f in os.listdir(dir_path):
            if f.endswith(".kicad_pcb"):
                return os.path.join(dir_path, f)
                
    parent_dir = os.path.dirname(dir_path)
    if os.path.isdir(parent_dir):
        for f in os.listdir(parent_dir):
            if f.endswith(".kicad_pcb"):
                return os.path.join(parent_dir, f)
                
    return ""
