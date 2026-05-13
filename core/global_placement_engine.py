"""
Global Placement Engine Integration
Handles placement computation using QML + gradient-based optimization
"""

import numpy as np
import json
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path
import torch
import time

logger = logging.getLogger(__name__)


class GlobalPlacementEngine:
    """Manages global placement computation with density control."""

    def __init__(self, config_path: str = "configs/ca234_sky130.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"[PLACEMENT_ENGINE] Loaded config: {self.config_path}")
        logger.info(f"[PLACEMENT_ENGINE] Using device: {self.device}")

    def _load_config(self) -> Dict:
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}. Using defaults.")
            return self._default_config()
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        return config

    @staticmethod
    def _default_config() -> Dict:
        return {
            "benchmark": "CA234",
            "design_name": "CA234",
            "pdk": "Sky130",
            "target_density": 0.55,
            "gpu": 1,
            "num_bins_x": 512,
            "num_bins_y": 512,
            "global_place_stages": [
                {
                    "iteration": 2000,
                    "learning_rate": 0.05,
                    "optimizer": "nesterov",
                    "density_weight": 8e-5
                }
            ],
            "legalize_flag": 1,
            "detailed_place_flag": 1,
            "detailed_place_engine": "ntuplace3"
        }

    def run_placement(self,
                      cell_data: Dict,
                      qml_model=None,
                      target_density: Optional[float] = None,
                      iterations: int = 2000,
                      learning_rate: float = 0.05,
                      callback=None) -> Tuple[np.ndarray, Dict]:
        """
        Run global placement with density control.

        Returns:
            Tuple of (placements, metrics)
            - placements: [N, 2] array with (x, y) in DBU
            - metrics: Dict with convergence info
        """
        if target_density is None:
            target_density = self.config.get('target_density', 0.55)

        start_time = time.time()

        cells = cell_data.get('cells', [])
        n_cells = len(cells)

        if n_cells == 0:
            logger.error("[PLACEMENT_ENGINE] No cells to place")
            return np.zeros((0, 2)), {'error': 'No cells'}

        logger.info(f"[PLACEMENT_ENGINE] Placing {n_cells} cells with target density {target_density:.2%}")

        die = cell_data.get('die', {})
        die_x0, die_y0 = die.get('x0', 0), die.get('y0', 0)
        die_x1, die_y1 = die.get('x1', 1000000), die.get('y1', 1000000)
        die_width  = die_x1 - die_x0
        die_height = die_y1 - die_y0

        # ── Initialization ────────────────────────────────────────────────────
        if qml_model is not None and n_cells < 100:
            logger.info("[PLACEMENT_ENGINE] Initializing with QML model...")
            try:
                from .qml_model import Sky130FeatureEncoder
                feature_encoder = Sky130FeatureEncoder(
                    die_area=(die_x0, die_y0, die_x1, die_y1)
                )
                features = feature_encoder.forward(cell_data)
                features_tensor = torch.tensor(features, dtype=torch.float32)
                coords_normalized = qml_model.forward(features_tensor)

                initial_placements = coords_normalized.cpu().numpy()
                initial_placements[:, 0] = initial_placements[:, 0] * die_width  + die_x0
                initial_placements[:, 1] = initial_placements[:, 1] * die_height + die_y0
                logger.info("[PLACEMENT_ENGINE] QML initialization complete")
            except Exception as e:
                logger.warning(f"[PLACEMENT_ENGINE] QML init failed ({e}). Using random.")
                initial_placements = self._random_initialization(cells, die)
        else:
            logger.info(f"[PLACEMENT_ENGINE] Using random initialization (n_cells={n_cells})")
            initial_placements = self._random_initialization(cells, die)

        # ── Optimization ──────────────────────────────────────────────────────
        placements = torch.tensor(
            initial_placements, dtype=torch.float32,
            device=self.device, requires_grad=True
        )

        # Build net connectivity tensor once (for fast HPWL)
        net_pairs = self._build_net_pairs(cell_data)
        logger.info(f"[DEBUG] Built {len(net_pairs)} net pairs from {len(cell_data.get('nets',[]))} nets")

        optimizer = torch.optim.SGD([placements], lr=learning_rate, momentum=0.9)

        metrics = {
            'iterations':       [],
            'hpwl_history':     [],
            'overflow_history': [],
            'loss_history':     []
        }

        # ── Early stopping — tuned for visible convergence ────────────────────
        best_loss     = float('inf')
        patience      = 200   # Allow more iterations for convergence
        no_improve_count = 0
        min_iterations   = 200  # Don't stop before cells cluster

        for iteration in range(iterations):
            optimizer.zero_grad()

            # Loss: net-based HPWL + density overflow
            hpwl_loss     = self._compute_wirelength_loss(placements, net_pairs)
            overflow_loss = self._compute_density_overflow(
                placements, cells, die, target_density
            )

            density_weight = (
                self.config
                    .get('global_place_stages', [{}])[0]
                    .get('density_weight', 8e-5)
            )
            total_loss = hpwl_loss + density_weight * overflow_loss

            total_loss.backward()
            
            optimizer.step()

            # Keep cells inside die
            with torch.no_grad():
                placements.data[:, 0].clamp_(die_x0, die_x1)
                placements.data[:, 1].clamp_(die_y0, die_y1)

            # Early stopping — count only if loss doesn't improve
            current_loss = float(total_loss.item())
            if current_loss < best_loss:  # Any improvement counts
                best_loss = current_loss
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Log every 10 iterations
            log_freq = max(1, min(10, iterations // 20))
            if iteration % log_freq == 0:
                elapsed = time.time() - start_time
                metrics['iterations'].append(iteration)
                metrics['hpwl_history'].append(float(hpwl_loss.item()))
                metrics['overflow_history'].append(float(overflow_loss.item()))
                metrics['loss_history'].append(float(total_loss.item()))

                effective_iters = min(
                    iterations,
                    max(min_iterations, iteration + patience - no_improve_count)
                )
                time_per_iter = elapsed / (iteration + 1) if iteration > 0 else 0.01
                eta_seconds   = max(1, int(time_per_iter * (effective_iters - iteration)))

                logger.info(
                    f"[PLACEMENT] Iter {iteration:4d}: "
                    f"HPWL={hpwl_loss.item():.6f}, "
                    f"Overflow={overflow_loss.item():.6f}, "
                    f"No-improve={no_improve_count}/{patience}, ETA={eta_seconds}s"
                )

                if callback:
                    callback(
                        iteration, effective_iters,
                        float(hpwl_loss.item()),
                        float(overflow_loss.item()),
                        eta_seconds
                    )

            if iteration >= min_iterations and no_improve_count >= patience:
                logger.info(
                    f"[PLACEMENT_ENGINE] Early stopping at iteration {iteration} "
                    f"(no improvement for {patience} iterations)"
                )
                break

        # ── Finalise ──────────────────────────────────────────────────────────
        final_placements = placements.detach().cpu().numpy()

        from .openroad_bridge import align_to_sky130_rows
        final_placements = align_to_sky130_rows(final_placements)

        elapsed = time.time() - start_time
        logger.info(f"[PLACEMENT_ENGINE] Placement complete in {elapsed:.2f}s")

        metrics['total_time'] = elapsed
        metrics['final_hpwl'] = self._compute_hpwl(final_placements, cell_data)

        return final_placements.astype(int), metrics

    # ──────────────────────────────────────────────────────────────────────────
    # Loss functions
    # ──────────────────────────────────────────────────────────────────────────

    def _build_net_pairs(self, cell_data: Dict):
        """
        Pre-compute (driver, sink) index pairs for all nets.
        Returns a list of (i, j) tuples — built once, reused every iteration.
        """
        cells    = cell_data.get('cells', [])
        nets     = cell_data.get('nets', [])
        cell_map = {cell['name']: idx for idx, cell in enumerate(cells)}

        pairs = []
        for net in nets:
            pins = net.get('pins', [])
            indices = [cell_map[p['cell']] for p in pins if p.get('cell') in cell_map]
            # Add consecutive pairs within each net
            for k in range(len(indices) - 1):
                pairs.append((indices[k], indices[k + 1]))

        return pairs

    def _compute_wirelength_loss(
        self,
        placements: torch.Tensor,
        net_pairs
    ) -> torch.Tensor:
        """
        Net-based HPWL approximation using log-sum-exp (differentiable).
        Falls back to centroid attraction when no net pairs are available.
        """
        if not net_pairs:
            # Fallback: Attract cells toward centroid (clustering)
            # Minimizing squared distance to centroid = encouraging cell clustering
            xs, ys       = placements[:, 0], placements[:, 1]
            mean_x       = xs.mean()
            mean_y       = ys.mean()
            centroid_loss = torch.sum((xs - mean_x) ** 2 + (ys - mean_y) ** 2)
            return centroid_loss / len(placements)

        # Convert net pairs to tensor indices for vectorized computation
        # This preserves gradients through indexing
        indices = torch.tensor(net_pairs, device=placements.device, dtype=torch.long)
        i_idx = indices[:, 0]
        j_idx = indices[:, 1]

        pi = placements[i_idx]   # (E, 2) — positions of first cell in each net
        pj = placements[j_idx]   # (E, 2) — positions of second cell in each net

        # Manhattan distance per net edge (differentiable)
        wirelength = torch.sum(torch.abs(pi - pj))
        # Scale by sqrt(num_pairs) instead of num_pairs to maintain gradient magnitude
        # This produces stronger gradients while still penalizing larger wirelengths
        return wirelength / (len(net_pairs) ** 0.5 + 1e-8)

    def _compute_density_overflow(
        self,
        placements: torch.Tensor,
        cells: list,
        die: Dict,
        target_density: float
    ) -> torch.Tensor:
        """Smooth density overflow penalty."""
        die_x0, die_y0 = die.get('x0', 0),       die.get('y0', 0)
        die_x1, die_y1 = die.get('x1', 1000000), die.get('y1', 1000000)
        die_area = (die_x1 - die_x0) * (die_y1 - die_y0)

        cell_area = sum(
            cell.get('width', 0) * cell.get('height', 0)
            for cell in cells
        )

        x_range   = placements[:, 0].max() - placements[:, 0].min()
        y_range   = placements[:, 1].max() - placements[:, 1].min()
        placed_area = (x_range + 1) * (y_range + 1)

        density         = cell_area / (placed_area + 1e-6)
        overflow_penalty = torch.relu(density - target_density)

        return overflow_penalty * 1000.0

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _random_initialization(self, cells: list, die: Dict) -> np.ndarray:
        n_cells = len(cells)
        die_x0, die_y0 = die.get('x0', 0), die.get('y0', 0)
        die_x1, die_y1 = die.get('x1', 1000000), die.get('y1', 1000000)

        placements       = np.zeros((n_cells, 2))
        placements[:, 0] = np.random.uniform(die_x0, die_x1, n_cells)
        placements[:, 1] = np.random.uniform(die_y0, die_y1, n_cells)
        return placements

    def _compute_hpwl(self, placements: np.ndarray, cell_data: Dict) -> float:
        """Exact HPWL in µm."""
        nets     = cell_data.get('nets', [])
        cells    = cell_data.get('cells', [])
        cell_map = {cell['name']: i for i, cell in enumerate(cells)}

        total_hpwl = 0.0
        for net in nets:
            pins = net.get('pins', [])
            if len(pins) < 2:
                continue
            xs, ys = [], []
            for pin in pins:
                cell_name = pin.get('cell')
                if cell_name in cell_map:
                    idx = cell_map[cell_name]
                    xs.append(placements[idx, 0])
                    ys.append(placements[idx, 1])
            if xs and ys:
                total_hpwl += (max(xs) - min(xs)) + (max(ys) - min(ys))

        return total_hpwl / 1000.0   # DBU → µm

    def compute_wirelength_metrics(self, cell_data: Dict) -> Dict:
        return {
            'hpwl':      self._compute_hpwl(
                np.array([[c['x'], c['y']] for c in cell_data.get('cells', [])]),
                cell_data
            ),
            'num_nets':  len(cell_data.get('nets', [])),
            'num_cells': len(cell_data.get('cells', []))
        }