#!/usr/bin/env python3
"""Test script to debug placement convergence issue."""

import logging
import numpy as np
import torch
from core.global_placement_engine import GlobalPlacementEngine

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Generate demo cell data (same as main_window)
n_cells = 10000
cell_data = {
    'cells': [
        {
            'name': f'cell_{i}',
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

logger.info(f"Generated {len(cell_data['cells'])} cells")

# Run placement
logger.info("Running placement...")
engine = GlobalPlacementEngine()
placements, metrics = engine.run_placement(
    cell_data, 
    iterations=500,
    learning_rate=0.05,
    target_density=0.55
)

logger.info(f"Placement complete.")
logger.info(f"Final placement range: X=[{placements[:, 0].min():.0f}, {placements[:, 0].max():.0f}], Y=[{placements[:, 1].min():.0f}, {placements[:, 1].max():.0f}]")
if metrics.get('hpwl_history'):
    logger.info(f"HPWL history: {metrics['hpwl_history'][:10]}...")
    logger.info(f"Iterations: {metrics.get('iterations', [])}...")

