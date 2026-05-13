"""
Physics-based visualization: Density Map, Electric Potential, Electric Field
"""

import logging
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import PowerNorm

logger = logging.getLogger(__name__)


class PhysicsVisualizer(QWidget):
    """Compute and display physics-based placement analysis."""

    def __init__(self, canvas_width=1_000_000, canvas_height=1_000_000, bin_size=50_000):
        super().__init__()
        self.canvas_width  = canvas_width
        self.canvas_height = canvas_height
        self.bin_size      = bin_size
        self.bins_x        = canvas_width  // bin_size   # 20 bins
        self.bins_y        = canvas_height // bin_size   # 20 bins

        self.placements  = None
        self.cell_sizes  = None
        self.density_map = None
        self.potential   = None
        self.field_x     = None
        self.field_y     = None
        self.iteration   = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        plt.style.use('dark_background')
        self.fig = Figure(figsize=(20, 5), dpi=100)
        self.fig.patch.set_facecolor('#1a1a1a')

        self.mpl_canvas = FigureCanvas(self.fig)
        layout.addWidget(self.mpl_canvas)

        btn_layout = QHBoxLayout()
        self.compute_btn = QPushButton("Compute Analysis")
        self.compute_btn.clicked.connect(self.compute_all)
        self.compute_btn.setEnabled(False)
        btn_layout.addWidget(self.compute_btn)

        self.export_btn = QPushButton("Export Data")
        btn_layout.addWidget(self.export_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def set_placement_data(
        self,
        placements_np: np.ndarray,
        cell_sizes_np: np.ndarray = None,
        iteration: int = 0
    ):
        """
        Store placement data and trigger auto-compute + render.

        Args:
            placements_np : (N, 2) float array — cell (x, y) in design units
            cell_sizes_np : (N, 2) float array — cell (w, h) in design units, or None
            iteration     : current iteration counter
        """
        self.placements = placements_np
        self.iteration  = iteration

        if cell_sizes_np is None:
            # Default: 1% of canvas as uniform cell size
            default_size = self.canvas_width * 0.01
            self.cell_sizes = np.full((len(placements_np), 2), default_size)
        else:
            self.cell_sizes = cell_sizes_np

        logger.info(
            f"[PHYSICS_VIZ] Loaded {len(placements_np)} cells  "
            f"x=[{placements_np[:,0].min():.0f}, {placements_np[:,0].max():.0f}]  "
            f"y=[{placements_np[:,1].min():.0f}, {placements_np[:,1].max():.0f}]  "
            f"iter={iteration}"
        )

        self.compute_btn.setEnabled(True)
        self.compute_all()

    # ──────────────────────────────────────────────────────────────────────────
    # Physics computations
    # ──────────────────────────────────────────────────────────────────────────

    def compute_density_map(self) -> np.ndarray:
        """
        Bin cells into a 2-D density grid.
        Uses more bins (50x50) for finer resolution so uniform distributions
        still show per-cell variation.
        """
        # 200x200 grid — at 10k cells, ~0.25 cells/bin average
        # so occupied bins stand out clearly against empty ones
        density_bins = 200
        density = np.zeros((density_bins, density_bins), dtype=float)

        x_scale = density_bins / self.canvas_width
        y_scale = density_bins / self.canvas_height

        for i, (x, y) in enumerate(self.placements):
            bx = int(np.clip(x * x_scale, 0, density_bins - 1))
            by = int(np.clip(y * y_scale, 0, density_bins - 1))
            density[by, bx] += 1

        self.density_map = density
        return density

    def compute_electric_potential(self) -> np.ndarray:
        """
        Electrostatic potential  φ = Σ 1/r  (smooth ePlace approximation).
        Subsamples to 2000 cells max for performance.
        """
        potential = np.zeros((self.bins_y, self.bins_x), dtype=float)

        y_coords = np.linspace(
            self.bin_size / 2,
            self.canvas_height - self.bin_size / 2,
            self.bins_y
        )
        x_coords = np.linspace(
            self.bin_size / 2,
            self.canvas_width - self.bin_size / 2,
            self.bins_x
        )
        xx, yy = np.meshgrid(x_coords, y_coords)

        # Subsample for speed
        cells = self.placements
        if len(cells) > 2000:
            idx   = np.random.choice(len(cells), 2000, replace=False)
            cells = cells[idx]

        for cell_x, cell_y in cells:
            dist      = np.sqrt((xx - cell_x) ** 2 + (yy - cell_y) ** 2) + 1e-6
            potential += 1.0 / dist

        self.potential = potential
        return potential

    def compute_electric_field(self) -> tuple:
        """E = -∇φ  (unit vectors)."""
        if self.potential is None:
            self.compute_electric_potential()

        gy, gx  = np.gradient(self.potential)
        mag     = np.sqrt(gx ** 2 + gy ** 2) + 1e-12
        self.field_x = gx / mag
        self.field_y = gy / mag
        return self.field_x, self.field_y

    def compute_all(self):
        """Compute every field and refresh the display."""
        if self.placements is None:
            logger.warning("[PHYSICS_VIZ] No placement data — skipping")
            return

        logger.info("[PHYSICS_VIZ] Computing density / potential / field …")
        self.compute_density_map()
        self.compute_electric_potential()
        self.compute_electric_field()
        self._plot_all()
        logger.info("[PHYSICS_VIZ] Analysis complete")

    # ──────────────────────────────────────────────────────────────────────────
    # Rendering
    # ──────────────────────────────────────────────────────────────────────────

    def _plot_all(self):
        """Four-panel dark dashboard."""
        self.fig.clear()
        self.fig.patch.set_facecolor('#1a1a1a')

        gs = self.fig.add_gridspec(
            1, 4,
            wspace=0.02, hspace=0.0,
            left=0.02, right=0.99, top=0.90, bottom=0.05
        )

        # ── Panel 0 : PLACEMENT ────────────────────────────────────────────────
        ax0 = self.fig.add_subplot(gs[0, 0])
        ax0.set_facecolor('#000000')

        # FIX: render cells as scatter dots instead of rectangles.
        # At 10k cells across a 1M-unit canvas, individual rectangles are
        # sub-pixel — scatter with a fixed marker size is far more readable.
        xs = self.placements[:, 0]
        ys = self.placements[:, 1]

        # Draw cells as filled circles (s = marker area in points²)
        ax0.scatter(xs, ys, s=4, c='#e05555', alpha=0.7,
                    linewidths=0, rasterized=True)

        # Blue wire overlay — ~400 random net connections
        n_wires = min(400, len(self.placements) - 1)
        wire_idx = np.random.choice(len(self.placements) - 1, n_wires, replace=False)
        for i in wire_idx:
            x1, y1 = self.placements[i]
            x2, y2 = self.placements[i + 1]
            ax0.plot([x1, x2], [y1, y2],
                     color='#3377ff', linewidth=0.3, alpha=0.25)

        ax0.set_xlim(0, self.canvas_width)
        ax0.set_ylim(0, self.canvas_height)
        ax0.set_aspect('equal')

        ax0.text(
            0.02, 0.04, f'Iter: {self.iteration}',
            transform=ax0.transAxes,
            fontsize=13, color='#4499ff', fontweight='bold',
            va='bottom', ha='left',
            bbox=dict(
                boxstyle='round,pad=0.3',
                facecolor='#000000', alpha=0.75,
                edgecolor='#4499ff', linewidth=1.2
            )
        )
        self._style_panel(ax0, 'BigBlue4')

        # ── Panel 1 : DENSITY MAP ──────────────────────────────────────────────
        ax1 = self.fig.add_subplot(gs[0, 1])
        ax1.set_facecolor('#000000')

        # Light smooth — keeps per-cell structure visible
        density_smooth = ndimage.gaussian_filter(self.density_map.astype(float), sigma=1.2)

        # Stretch vmax to 95th percentile of occupied bins only so even
        # uniform/sparse placements show clear bright spots on black bg
        occupied = density_smooth[density_smooth > 0]
        vmax_d = float(np.percentile(occupied, 95)) if len(occupied) > 0 else 1.0

        ax1.imshow(
            density_smooth,
            cmap='gray_r',          # black bg, white = high density
            origin='lower', aspect='auto',
            interpolation='bilinear',
            vmin=0, vmax=max(vmax_d, 1e-6)
        )
        self._style_panel(ax1, 'Density Map')

        # ── Panel 2 : ELECTRIC POTENTIAL ──────────────────────────────────────
        ax2 = self.fig.add_subplot(gs[0, 2])
        ax2.set_facecolor('#000000')

        potential_smooth = ndimage.gaussian_filter(self.potential, sigma=3)
        ax2.imshow(
            potential_smooth,
            cmap='twilight_shifted', origin='lower', aspect='auto',
            interpolation='bilinear'
        )
        self._style_panel(ax2, 'Electric Potential')

        # ── Panel 3 : ELECTRIC FIELD ───────────────────────────────────────────
        ax3 = self.fig.add_subplot(gs[0, 3])
        ax3.set_facecolor('#000000')

        gy, gx           = np.gradient(self.potential)
        field_mag        = np.sqrt(gx ** 2 + gy ** 2)
        field_mag_smooth = ndimage.gaussian_filter(field_mag, sigma=1.5)

        # FIX: use percentile vmax so the background isn't black when
        # field is nearly uniform
        vmax_f = np.percentile(field_mag_smooth, 99)
        vmin_f = field_mag_smooth.min()

        ax3.imshow(
            field_mag_smooth,
            cmap='gray', origin='lower', aspect='auto',
            interpolation='bilinear',
            norm=PowerNorm(
                gamma=0.4,
                vmin=vmin_f,
                vmax=max(vmax_f, vmin_f + 1e-12)
            )
        )

        # Quiver overlay on top
        step   = max(1, self.bins_x // 12)
        y_q    = np.linspace(0, self.canvas_height, self.bins_y)[::step]
        x_q    = np.linspace(0, self.canvas_width,  self.bins_x)[::step]
        xx, yy = np.meshgrid(x_q, y_q)
        fx     = self.field_x[::step, ::step]
        fy     = self.field_y[::step, ::step]
        ax3.quiver(xx, yy, fx, fy,
                   alpha=0.35, color='#aaaaaa', scale=45, width=0.003)

        self._style_panel(ax3, 'Electric Field')

        self.mpl_canvas.draw()

    def _style_panel(self, ax, title: str):
        """Uniform dark-dashboard panel styling."""
        ax.set_title(title, color='white', fontsize=14, fontweight='bold', pad=8)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor('white')
            spine.set_linewidth(1.5)
            spine.set_visible(True)

    # ──────────────────────────────────────────────────────────────────────────
    # Stats helper
    # ──────────────────────────────────────────────────────────────────────────

    def get_analysis_stats(self) -> dict:
        if self.placements is None:
            return {}
        return {
            'num_cells':      len(self.placements),
            'density_mean':   float(np.mean(self.density_map))  if self.density_map is not None else 0,
            'density_max':    float(np.max(self.density_map))   if self.density_map is not None else 0,
            'potential_mean': float(np.mean(self.potential))    if self.potential   is not None else 0,
            'field_mean':     float(np.mean(
                                  np.sqrt(self.field_x ** 2 + self.field_y ** 2)
                              ))                                 if self.field_x    is not None else 0,
        }