import re

# Supported library packages in footprints.blend
AVAILABLE_PACKAGES = [
    "R_0402", "R_0603", "R_0805", "R_1206",
    "C_0402", "C_0603", "C_0805", "C_1206",
    "SOT-23", "SOT-23-6", "SOT-223", "TO-252",
    "SOIC-8", "TSSOP-8", "SOIC-16", "QFN-32",
    "IND_5050", "POT_PTV09A", "SW_Slide_WS_SLTV"
]

PACKAGE_DESCRIPTIONS = {
    "R_0402": "SMD Resistor 0402 (1.00 x 0.50 mm)",
    "R_0603": "SMD Resistor 0603 (1.60 x 0.80 mm)",
    "R_0805": "SMD Resistor 0805 (2.00 x 1.25 mm)",
    "R_1206": "SMD Resistor 1206 (3.20 x 1.60 mm)",
    "C_0402": "SMD MLCC Capacitor 0402 (1.00 x 0.50 mm)",
    "C_0603": "SMD MLCC Capacitor 0603 (1.60 x 0.80 mm)",
    "C_0805": "SMD MLCC Capacitor 0805 (2.00 x 1.25 mm)",
    "C_1206": "SMD MLCC Capacitor 1206 (3.20 x 1.60 mm)",
    "SOT-23": "SOT-23 3-Pin Discrete Transistor Package",
    "SOT-23-6": "SOT-23-6 / SOT-23-6L (6-Pin, 0.95mm pitch) IC",
    "SOT-223": "SOT-223 4-Pin / Tab Voltage Regulator",
    "TO-252": "TO-252 / DPAK Power MOSFET / Diode Package",
    "SOIC-8": "SOIC-8 / SOP-8 (8-Pin, 1.27mm Pitch) Integrated Circuit",
    "TSSOP-8": "TSSOP-8 / SOP-8 (8-Pin, 0.65mm Pitch) IC (FS8205A, etc.)",
    "SOIC-16": "SOIC-16 / SOP-16 (16-Pin, 1.27mm Pitch) Integrated Circuit",
    "QFN-32": "QFN-32 / MLF-32 (5.0 x 5.0 mm, 0.5mm Pitch) IC",
    "IND_5050": "SMD Shielded Power Inductor 5050 (5.0 x 5.0 mm, NR-50xx)",
    "POT_PTV09A": "Bourns PTV09A 9mm Vertical Potentiometer with Metal Shaft",
    "SW_Slide_WS_SLTV": "Würth WS-SLTV Slide Switch SMD (8.7 x 3.0 mm)",
}

# Metric to Imperial code mapping for passive SMD chips
METRIC_TO_IMPERIAL = {
    "1005": "0402",
    "1608": "0603",
    "2012": "0805",
    "3216": "1206",
}

def tokenize(text):
    """Splits a footprint name or string into clean uppercase tokens"""
    if not text:
        return []
    raw_tokens = re.split(r'[^a-zA-Z0-9]+', text.upper())
    tokens = [t for t in raw_tokens if t]
    return tokens

def detect_passive_size(tokens):
    """Finds standard SMD passive size (0402, 0603, 0805, 1206) in tokens"""
    valid_sizes = {"0402", "0603", "0805", "1206"}
    for t in tokens:
        if t in valid_sizes:
            return t
        if t in METRIC_TO_IMPERIAL:
            return METRIC_TO_IMPERIAL[t]
        for size in valid_sizes:
            if size in t and not any(ic in t for ic in ["SOIC", "SOT", "QFN", "QFP", "PTV"]):
                return size
    return None

def match_footprint(ref, fp_name, value=""):
    """
    Intelligent token-based footprint matcher:
    Examines component reference (e.g. R1, C16, U5, Q2, L1), footprint name, and value.
    Returns:
        (matched_package_name, confidence_score)
        or (None, 0.0) if no match could be confidently determined.
    """
    ref_prefix = ''.join([c for c in ref if c.isalpha()]).upper()
    
    # Explicitly ignore bare copper test points
    if ref_prefix == 'TP' or "TESTPOINT" in fp_name.upper():
        return None, 0.0
        
    combined_str = f"{ref} {fp_name} {value}".upper()
    tokens = tokenize(combined_str)
    token_set = set(tokens)
    
    # 1. Inductors (Bobinler)
    if ref_prefix in ['L', 'IND'] or "INDUCTOR" in combined_str:
        if any(k in combined_str for k in ["NR_50", "NR-50", "50XX", "5050", "5040"]):
            return "IND_5050", 0.95
            
    # 2. Potentiometers (Potlar)
    if "PTV09A" in combined_str or ("POTENTIOMETER" in combined_str and "PTV09" in combined_str):
        return "POT_PTV09A", 0.95
        
    # 2.5 Switches & Buttons (Sürgülü Anahtar)
    if ref_prefix in ['SW', 'S'] or "SWITCH" in combined_str:
        if any(k in combined_str for k in ["WS_SLTV", "WS-SLTV", "SLTV", "SW_SLIDE"]):
            return "SW_Slide_WS_SLTV", 0.95
            
    # 3. Transistors & Small Regulators (SOT, TO)
    # SOT-223
    if any("SOT223" in t for t in tokens) or ("SOT" in token_set and "223" in token_set):
        return "SOT-223", 0.95
        
    # SOT-23-6 / SOT-23-6L (6-pin SOT-23 like FP6291)
    if any("SOT236" in t for t in tokens) or ("SOT" in token_set and "23" in token_set and any(k in token_set for k in ["6", "6L", "6P"])):
        return "SOT-23-6", 0.95
    if re.search(r'SOT-?23-?6L?', fp_name.upper()):
        return "SOT-23-6", 0.95
        
    # SOT-23 (3-pin discrete package)
    if any("SOT23" in t for t in tokens) or ("SOT" in token_set and "23" in token_set):
        return "SOT-23", 0.90
        
    # TO-252 / DPAK
    if any(t in ["TO252", "DPAK", "TO-252"] for t in tokens) or ("TO" in token_set and "252" in token_set):
        return "TO-252", 0.95
        
    # 4. ICs (SOIC, TSSOP, QFN)
    # QFN-32
    if any("QFN32" in t or "MLF32" in t for t in tokens) or ("QFN" in token_set and "32" in token_set):
        return "QFN-32", 0.95
        
    # TSSOP-8 / SOP65P (0.65 mm pitch 8-pin like FS8205A)
    if "SOP65P" in combined_str or "TSSOP-8" in combined_str or "TSSOP8" in token_set or "MSOP-8" in combined_str:
        return "TSSOP-8", 0.95
        
    # SOIC-16 / SOP-16
    if any("SOIC16" in t or "SOP16" in t or "SO16" in t for t in tokens) or \
       (("SOIC" in token_set or "SOP" in token_set) and "16" in token_set):
        return "SOIC-16", 0.95
        
    # SOIC-8 / SOP-8 (1.27 mm pitch 8-pin)
    if re.search(r'SO(?:IC|P).*?-?8(?:N|L|P|EP)?\b', fp_name.upper()) and "SOP65" not in fp_name.upper():
        return "SOIC-8", 0.95
    if any(t in ["SOIC8", "SO8"] for t in tokens):
        return "SOIC-8", 0.95
    if ("SOIC" in token_set or "SOP" in token_set) and any(n in token_set for n in ["8", "8N", "8L", "8EP"]):
        if "SOP65P" not in combined_str and "065" not in combined_str:
            return "SOIC-8", 0.95

    # 5. Passive SMD Chips (Resistors & Capacitors)
    passive_size = detect_passive_size(tokens)
    if passive_size:
        is_resistor = False
        is_capacitor = False
        
        if ref_prefix in ['R', 'RN', 'VR'] or any(k in token_set for k in ['RESISTOR', 'RES']):
            # Don't mistake potentiometers for tiny SMD resistors
            if "POTENTIOMETER" not in combined_str:
                is_resistor = True
        elif ref_prefix in ['C', 'CP'] or any(k in token_set for k in ['CAPACITOR', 'CAP', 'MLCC']):
            is_capacitor = True
            
        if not is_resistor and not is_capacitor:
            if "RESISTOR" in combined_str or "R_" in fp_name:
                is_resistor = True
            elif "CAPACITOR" in combined_str or "C_" in fp_name:
                is_capacitor = True
                
        if is_resistor:
            return f"R_{passive_size}", 0.90
        elif is_capacitor:
            return f"C_{passive_size}", 0.90
        elif ref_prefix.startswith('R'):
            return f"R_{passive_size}", 0.85
        elif ref_prefix.startswith('C'):
            return f"C_{passive_size}", 0.85

    return None, 0.0
