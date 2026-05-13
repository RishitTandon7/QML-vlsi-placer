"""
OpenROAD Bridge: Extract/write cell placement data from/to OpenROAD database
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import os
import sys


def extract_from_openroad(db) -> Dict:
    """
    Extract design data from OpenROAD odb database.
    
    Returns dict with keys:
    - 'cells': list of dicts with {name, width, height, x, y, fixed, pins, fanout, fanin}
    - 'nets': list of dicts with {name, pins}
    - 'die': {x0, y0, x1, y1}
    - 'rows': list of dicts with {x, y, width, site}
    - 'units': DBU per micron (1000 for Sky130)
    """
    try:
        import odb
    except ImportError:
        print("[ERROR] odb module not found. Ensure OpenROAD is installed with Python bindings.")
        return None
    
    db_units = db.getTech().getDbUnitsPerMicron()  # 1000 for Sky130
    block = db.getChip().getBlock()
    
    # Extract die area
    die = block.getDieBBox()
    die_data = {
        'x0': die.xMin(),
        'y0': die.yMin(),
        'x1': die.xMax(),
        'y1': die.yMax()
    }
    
    # Extract cells/instances
    cells = []
    cell_name_map = {}
    
    insts = block.getInsts()
    for inst in insts:
        master = inst.getMaster()
        loc = inst.getLocation()
        
        # Get placement status
        placement_status = inst.getPlacementStatus()
        is_fixed = (placement_status == 'FIXED' or 
                   placement_status == 'LOCKED' or
                   inst.isFixed())
        
        cell_info = {
            'name': inst.getName(),
            'master': master.getName(),
            'width': master.getWidth(),
            'height': master.getHeight(),
            'x': loc[0],
            'y': loc[1],
            'fixed': is_fixed,
            'pins': master.getMTerms().size() if hasattr(master, 'getMTerms') else 0,
            'fanout': 0,  # Will calculate from nets
            'fanin': 0    # Will calculate from nets
        }
        cells.append(cell_info)
        cell_name_map[inst.getName()] = len(cells) - 1
    
    # Extract nets
    nets = []
    net_list = block.getNets()
    
    for net in net_list:
        # Skip power nets for feature extraction
        net_name = net.getName()
        if any(pw in net_name for pw in ['VDD', 'VSS', 'VPWR', 'VGND', 'GND']):
            continue
        
        pins = []
        iterm_list = net.getITerms()
        for iterm in iterm_list:
            inst = iterm.getInst()
            if inst:
                pins.append({'cell': inst.getName()})
        
        # Update fanout/fanin counts
        for pin in pins:
            if pin['cell'] in cell_name_map:
                cell_idx = cell_name_map[pin['cell']]
                cells[cell_idx]['fanout'] += 1
        
        net_info = {
            'name': net_name,
            'pins': pins
        }
        nets.append(net_info)
    
    result = {
        'cells': cells,
        'nets': nets,
        'die': die_data,
        'rows': extract_rows(block, db_units),
        'units': db_units
    }
    
    print(f"[OPENROAD] Extracted {len(cells)} cells, {len(nets)} nets")
    return result


def extract_rows(block, db_units: int) -> List[Dict]:
    """Extract row information from OpenROAD database."""
    rows = []
    
    try:
        row_list = block.getRows()
        for row in row_list:
            bb = row.getBBox()
            site = row.getSite()
            site_name = site.getName() if site else "unithd"
            
            row_info = {
                'x': bb.xMin(),
                'y': bb.yMin(),
                'width': bb.xMax() - bb.xMin(),
                'site': site_name
            }
            rows.append(row_info)
    except:
        # Fallback: estimate rows from die height and Sky130 row height
        print("[OPENROAD] Could not extract rows directly, using default estimation")
        die = block.getDieBBox()
        die_height = die.yMax() - die.yMin()
        row_height_dbu = 2720  # Sky130 row height in DBU
        
        y = die.yMin()
        while y < die.yMax():
            rows.append({
                'x': die.xMin(),
                'y': y,
                'width': die.xMax() - die.xMin(),
                'site': 'unithd'
            })
            y += row_height_dbu
    
    return rows


def write_back_to_openroad(db, placements: np.ndarray, cell_names: List[str]):
    """
    Write placement coordinates back to OpenROAD odb database.
    
    Args:
        db: OpenROAD database handle
        placements: Array [N, 2] with (x, y) in DBU
        cell_names: List of cell instance names
    """
    try:
        import odb
    except ImportError:
        print("[ERROR] odb module not found")
        return False
    
    block = db.getChip().getBlock()
    
    written = 0
    for i, name in enumerate(cell_names):
        try:
            inst = block.findInst(name)
            if inst and not inst.isFixed():
                x = int(placements[i, 0])
                y = int(placements[i, 1])
                inst.setLocation(x, y)
                inst.setPlacementStatus('PLACED')
                written += 1
        except Exception as e:
            print(f"[ERROR] Could not place {name}: {e}")
    
    print(f"[OPENROAD] Wrote placement for {written} cells")
    return written > 0


def sky130_feature_extraction(cell_data: Dict) -> np.ndarray:
    """
    Extract Sky130-specific features for each cell.
    
    Features per cell (8):
    [norm_width, norm_height, pin_count, fanout, fanin,
     norm_x_init, norm_y_init, connectivity_score]
    
    All normalized to [0, 1].
    """
    cells = cell_data.get('cells', [])
    die = cell_data.get('die', {})
    
    if not cells:
        return np.zeros((0, 8))
    
    n_cells = len(cells)
    features = np.zeros((n_cells, 8))
    
    # Sky130 site dimensions (DBU)
    SITE_WIDTH = 460  # 0.46 µm
    SITE_HEIGHT = 2720  # 2.72 µm
    
    # Die dimensions
    die_width = die.get('x1', 1000000) - die.get('x0', 0)
    die_height = die.get('y1', 1000000) - die.get('y0', 0)
    
    for i, cell in enumerate(cells):
        # Feature 0: Normalized width
        width = cell.get('width', 0)
        features[i, 0] = min(1.0, width / (SITE_WIDTH * 10))
        
        # Feature 1: Normalized height
        height = cell.get('height', 0)
        features[i, 1] = min(1.0, height / SITE_HEIGHT)
        
        # Feature 2: Pin count normalized
        pins = cell.get('pins', 0)
        features[i, 2] = min(1.0, pins / 20.0)
        
        # Feature 3: Fanout normalized
        fanout = cell.get('fanout', 0)
        features[i, 3] = min(1.0, fanout / 50.0)
        
        # Feature 4: Fanin normalized
        fanin = cell.get('fanin', 0)
        features[i, 4] = min(1.0, fanin / 50.0)
        
        # Feature 5: Normalized initial X
        x = cell.get('x', 0)
        features[i, 5] = (x - die.get('x0', 0)) / die_width if die_width > 0 else 0.5
        
        # Feature 6: Normalized initial Y
        y = cell.get('y', 0)
        features[i, 6] = (y - die.get('y0', 0)) / die_height if die_height > 0 else 0.5
        
        # Feature 7: Connectivity score
        conn = (pins + fanout + fanin) / 100.0
        features[i, 7] = min(1.0, conn)
    
    # Ensure all features in [0, 1]
    features = np.clip(features, 0.0, 1.0)
    
    return features


def load_openroad_design(lef_files: List[str], def_file: str):
    """
    Load LEF and DEF files into OpenROAD database.
    
    Args:
        lef_files: List of LEF file paths
        def_file: DEF file path
        
    Returns:
        OpenROAD db object
    """
    try:
        import openroad
        import odb
    except ImportError:
        print("[ERROR] OpenROAD Python bindings not found")
        return None
    
    # Create OpenROAD application
    ordb = openroad.OpenRoad()
    
    # Read LEF files
    for lef in lef_files:
        if os.path.exists(lef):
            print(f"[OPENROAD] Reading LEF: {lef}")
            ordb.readLef(lef)
        else:
            print(f"[WARN] LEF file not found: {lef}")
    
    # Read DEF file
    if os.path.exists(def_file):
        print(f"[OPENROAD] Reading DEF: {def_file}")
        ordb.readDef(def_file)
    else:
        print(f"[ERROR] DEF file not found: {def_file}")
        return None
    
    return ordb.getDb()


def snap_to_grid(coordinate: float, grid_size: float) -> float:
    """Snap coordinate to grid (e.g., Sky130 site width or row height)."""
    return round(coordinate / grid_size) * grid_size


def align_to_sky130_rows(placements: np.ndarray, row_height_dbu: int = 2720) -> np.ndarray:
    """
    Align Y coordinates to Sky130 rows.
    
    Args:
        placements: [N, 2] array with (x, y) in DBU
        row_height_dbu: Sky130 row height (2.72 µm = 2720 DBU)
        
    Returns:
        Aligned placements
    """
    aligned = placements.copy()
    aligned[:, 1] = np.round(aligned[:, 1] / row_height_dbu) * row_height_dbu
    return aligned


def compute_hpwl(cells: Dict, nets: Dict) -> float:
    """
    Compute Half-Perimeter Wire Length for current placement.
    
    Returns:
        HPWL in µm (DBU ÷ 1000)
    """
    total_hpwl = 0.0
    
    for net in nets.get('nets', []):
        if len(net.get('pins', [])) < 2:
            continue
        
        # Get cell positions for this net
        xs, ys = [], []
        for pin in net['pins']:
            cell_name = pin.get('cell')
            for cell in nets.get('cells', []):
                if cell['name'] == cell_name:
                    xs.append(cell['x'])
                    ys.append(cell['y'])
                    break
        
        if xs and ys:
            hpwl = (max(xs) - min(xs)) + (max(ys) - min(ys))
            total_hpwl += hpwl
    
    return total_hpwl / 1000.0  # Convert DBU to µm
