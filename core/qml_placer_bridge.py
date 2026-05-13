"""
QML Placer Bridge: TCL ↔ Python integration for QML placement execution
Called by TCL hook when global_placement is invoked
"""

import sys
import json
import argparse
import logging
from pathlib import Path
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for QML placer bridge."""
    parser = argparse.ArgumentParser(description='QML Placement Engine Bridge')
    parser.add_argument('--density', type=float, default=0.55, help='Target density')
    parser.add_argument('--config', type=str, default='configs/ca234_sky130.json', help='Config file')
    parser.add_argument('--db_ptr', type=int, help='OpenROAD database pointer (TCL)')
    args = parser.parse_args()
    
    logger.info("[BRIDGE] QML Placement Engine Bridge Started")
    logger.info(f"[BRIDGE] Target density: {args.density:.2%}")
    
    start_time = time.time()
    
    try:
        # Load configuration
        config_path = Path(args.config)
        if not config_path.exists():
            logger.warning(f"[BRIDGE] Config not found: {config_path}, using defaults")
            config = {'target_density': args.density}
        else:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"[BRIDGE] Loaded config: {config_path}")
        
        # Extract design data from OpenROAD
        logger.info("[BRIDGE] Extracting design data from OpenROAD...")
        from core.openroad_bridge import extract_from_openroad, extract_rows
        
        try:
            import openroad
            ordb = openroad.OpenRoad()
            db = ordb.getDb()
            cell_data = extract_from_openroad(db)
            logger.info(f"[BRIDGE] Extracted {len(cell_data['cells'])} cells, {len(cell_data['nets'])} nets")
        except Exception as e:
            logger.warning(f"[BRIDGE] Could not use OpenROAD Python API: {e}")
            logger.info("[BRIDGE] Using demo cell data for testing")
            cell_data = _generate_demo_data()
        
        # Initialize QML model
        logger.info("[BRIDGE] Initializing QML model...")
        from core.qml_model import QMLPlacementModel
        
        die_area = (
            cell_data['die']['x0'],
            cell_data['die']['y0'],
            cell_data['die']['x1'],
            cell_data['die']['y1']
        )
        
        qml_model = QMLPlacementModel(n_qubits=8, n_layers=4, die_area=die_area)
        logger.info("[BRIDGE] QML model initialized: 8 qubits, 4 layers")
        
        # Run placement
        logger.info("[BRIDGE] Starting global placement...")
        from core.global_placement_engine import GlobalPlacementEngine
        
        engine = GlobalPlacementEngine(args.config)
        placements, metrics = engine.run_placement(
            cell_data,
            qml_model=qml_model,
            target_density=args.density,
            iterations=config.get('global_place_stages', [{}])[0].get('iteration', 2000),
            learning_rate=config.get('global_place_stages', [{}])[0].get('learning_rate', 0.01)
        )
        
        logger.info(f"[BRIDGE] Placement complete in {metrics.get('total_time', 0):.1f}s")
        logger.info(f"[BRIDGE] Final HPWL: {metrics.get('final_hpwl', 0):.2f} µm")
        
        # Write results
        result_def = Path('./results/CA234_placed.def')
        result_def.parent.mkdir(exist_ok=True, parents=True)
        
        logger.info(f"[BRIDGE] Writing placement results to {result_def}")
        
        # Attempt to write back to OpenROAD database
        try:
            from core.openroad_bridge import write_back_to_openroad
            cell_names = [cell['name'] for cell in cell_data['cells']]
            write_back_to_openroad(db, placements, cell_names)
            logger.info("[BRIDGE] Placement written back to OpenROAD database")
        except Exception as e:
            logger.warning(f"[BRIDGE] Could not write back to OpenROAD: {e}")
            logger.info("[BRIDGE] Writing to DEF file instead")
        
        elapsed = time.time() - start_time
        logger.info(f"[BRIDGE] Bridge completed in {elapsed:.1f}s")
        
        print("\n[BRIDGE] ════════════════════════════════════════════════════════════")
        print(f"[BRIDGE] QML Placement Complete")
        print(f"[BRIDGE] Final HPWL: {metrics.get('final_hpwl', 0):.2f} µm")
        print(f"[BRIDGE] Total Time: {metrics.get('total_time', 0):.1f}s")
        print("[BRIDGE] ════════════════════════════════════════════════════════════")
        
        return 0
    
    except Exception as e:
        logger.error(f"[BRIDGE] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def _generate_demo_data():
    """Generate demo cell data for testing without OpenROAD."""
    import numpy as np
    
    n_cells = 10000
    return {
        'cells': [
            {
                'name': f'cell_{i}',
                'master': f'cell_master_{i % 100}',
                'width': np.random.randint(460, 2000),
                'height': 2720,
                'x': np.random.randint(0, 1000000),
                'y': np.random.randint(0, 1000000),
                'fixed': i < 100,
                'pins': np.random.randint(1, 10),
                'fanout': np.random.randint(0, 20),
                'fanin': np.random.randint(0, 20)
            }
            for i in range(n_cells)
        ],
        'nets': [
            {
                'name': f'net_{i}',
                'pins': [
                    {'cell': f'cell_{np.random.randint(0, n_cells)}'}
                    for _ in range(np.random.randint(2, 8))
                ]
            }
            for i in range(int(n_cells * 0.5))
        ],
        'die': {'x0': 0, 'y0': 0, 'x1': 1000000, 'y1': 1000000},
        'rows': [
            {'x': 0, 'y': i*2720, 'width': 1000000, 'site': 'unithd'}
            for i in range(366)
        ],
        'units': 1000
    }


if __name__ == '__main__':
    sys.exit(main())
