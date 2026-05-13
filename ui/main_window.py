"""
Main Window: Top-level UI container for QML·PLACE
"""

import logging
import numpy as np
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QMenuBar, QMenu, QToolBar, QStatusBar, QMessageBox,
                             QSplitter, QFileDialog, QProgressDialog, QTabWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction, QKeySequence

from ui.sidebar import SidebarPanel
from ui.canvas_widget import PlacementCanvasWidget
from ui.charts_widget import ChartsPanel
from ui.gpu_panel import GPUPanel
from ui.progress_widget import ProgressPanel
from ui.stats_table import StatsTableWidget
from ui.log_console import LogConsole
from ui.physics_visualizer import PhysicsVisualizer
from core.placement_thread import PlacementWorkerThread, ComparisonWorkerThread

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("QML·PLACE — OpenROAD Sky130 CA234")
        self.setMinimumSize(1400, 900)

        # State
        self.cell_data         = None
        self.current_placement = None
        self.placement_worker  = None
        self.comparison_worker = None

        # PyTorch device
        import torch
        self.pytorch_device = "CUDA" if torch.cuda.is_available() else "CPU"
        logger.info(f"[MAIN_WINDOW] PyTorch device: {self.pytorch_device}")

        # QML model
        try:
            from core.qml_model import QuantumPlacementCircuit
            self.qml_model = QuantumPlacementCircuit(
                n_qubits=8, n_layers=4, diff_method="adjoint"
            )
            logger.info(
                f"[MAIN_WINDOW] QML Model on {self.qml_model.device_name}, "
                f"optimisation on {self.pytorch_device}"
            )
        except Exception as e:
            logger.warning(f"[MAIN_WINDOW] Failed to init QML model: {e}")
            self.qml_model = None

        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_status_bar()

        logger.info("[MAIN_WINDOW] Initialized")

    # ──────────────────────────────────────────────────────────────────────────
    # UI setup
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        file_menu.addAction("Open DEF...").triggered.connect(self._open_def)
        file_menu.addAction("Open Netlist...").triggered.connect(self._open_netlist)
        file_menu.addSeparator()
        file_menu.addAction("Save Config...").triggered.connect(self._save_config)
        file_menu.addAction("Export Results...").triggered.connect(self._export_results)
        file_menu.addSeparator()
        file_menu.addAction("Exit").triggered.connect(self.close)

        run_menu = menubar.addMenu("Run")
        run_menu.addAction("▶ Start QML Placement").triggered.connect(self._start_placement)
        run_menu.addAction("■ Stop").triggered.connect(self._stop_placement)
        run_menu.addSeparator()
        run_menu.addAction("Run Full OpenROAD Flow").triggered.connect(self._run_full_flow)
        run_menu.addAction("Run Standard Placer").triggered.connect(self._run_standard_placer)
        run_menu.addAction("Demo Mode").triggered.connect(self._run_demo)

        view_menu = menubar.addMenu("View")
        view_menu.addAction("Toggle Log").triggered.connect(self._toggle_log)
        view_menu.addAction("Toggle Stats").triggered.connect(self._toggle_stats)
        view_menu.addAction("Fullscreen").triggered.connect(self._toggle_fullscreen)

        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("OpenROAD Settings...").triggered.connect(self._openroad_settings)
        tools_menu.addAction("QML Config...").triggered.connect(self._qml_settings)
        tools_menu.addAction("PDK Path Settings...").triggered.connect(self._pdk_settings)
        tools_menu.addAction("Clear History").triggered.connect(self._clear_history)

        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About").triggered.connect(self._show_about)

    def _setup_toolbar(self):
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)

        toolbar.addAction("▶ QML Run").triggered.connect(self._start_placement)
        toolbar.addAction("⚖ Compare").triggered.connect(self._start_comparison)
        toolbar.addSeparator()
        toolbar.addAction("📂 Open DEF").triggered.connect(self._open_def)
        toolbar.addAction("📊 Report").triggered.connect(self._generate_report)
        toolbar.addAction("💾 Save DEF").triggered.connect(self._save_def)

    def _setup_central_widget(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Left sidebar
        self.sidebar = SidebarPanel()
        self.sidebar.run_placement.connect(self._start_placement)
        self.sidebar.setMaximumWidth(220)

        # Centre: canvas + tabbed results
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.canvas = PlacementCanvasWidget()
        splitter.addWidget(self.canvas)

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.South)

        self.charts = ChartsPanel()
        tabs.addTab(self.charts, "📊 Metrics")

        # ── FIX: canvas_width / canvas_height must match design-unit coordinate space ──
        # Demo cells use x/y in range [0, 1_000_000] (1 unit = 1 nm, die = 1000 µm)
        self.physics_viz = PhysicsVisualizer(
            canvas_width=1_000_000,
            canvas_height=1_000_000,
            bin_size=50_000          # 50 µm bins → 20×20 grid
        )
        tabs.addTab(self.physics_viz, "⚛ Physics")

        self.stats_table = StatsTableWidget()
        tabs.addTab(self.stats_table, "📈 History")

        self.log_console = LogConsole()
        tabs.addTab(self.log_console, "📝 Log")

        splitter.addWidget(tabs)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        # Right: GPU & Progress
        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)

        self.progress_panel = ProgressPanel()
        right_layout.addWidget(self.progress_panel)

        self.gpu_panel = GPUPanel(
            qml_model=self.qml_model,
            pytorch_device=self.pytorch_device
        )
        right_layout.addWidget(self.gpu_panel)
        right_layout.addStretch()

        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        right_widget.setMaximumWidth(180)

        main_layout.addWidget(self.sidebar,      stretch=0)
        main_layout.addWidget(splitter,          stretch=1)
        main_layout.addWidget(right_widget,      stretch=0)

    def _setup_status_bar(self):
        self.statusBar().showMessage("Ready")

    # ──────────────────────────────────────────────────────────────────────────
    # Placement control
    # ──────────────────────────────────────────────────────────────────────────

    def _start_placement(self):
        self.log_console.log("[MAIN] Starting QML placement...")
        self.progress_panel.reset()

        self.placement_worker = PlacementWorkerThread()
        self.placement_worker.stage_changed.connect(self._on_stage_changed)
        self.placement_worker.iteration_updated.connect(self._on_iteration_updated)
        self.placement_worker.placement_complete.connect(self._on_placement_complete)
        self.placement_worker.error_occurred.connect(self._on_placement_error)
        self.placement_worker.log_message.connect(self.log_console.log)

        config = self.sidebar.get_placement_config()
        self.placement_worker.set_placement_config(config)

        self.cell_data = self._generate_demo_cells()
        self.placement_worker.set_cell_data(self.cell_data)

        if self.qml_model:
            self.placement_worker.set_qml_model(self.qml_model)

        self.placement_worker.start()

    def _on_stage_changed(self, stage_name: str, percentage: int):
        self.progress_panel.set_stage(stage_name, percentage)

    def _on_iteration_updated(self, current: int, total: int,
                               hpwl: float, overflow: float, eta_seconds: int = 0):
        self.progress_panel.update_iteration(current, total, hpwl, overflow, eta_seconds)

    def _on_placement_complete(self, placements, metrics):
        """Handle placement completion and feed physics visualizer."""
        self.log_console.log(
            f"[MAIN] Placement complete! HPWL={metrics.get('final_hpwl', 0):.2f}µm"
        )
        self.canvas.set_placements(placements)
        self.stats_table.add_run(placements, metrics)

        # Convert to numpy regardless of source type
        if isinstance(placements, np.ndarray):
            placements_np = placements
        else:
            import torch
            if isinstance(placements, torch.Tensor):
                placements_np = placements.detach().cpu().numpy()
            else:
                placements_np = np.array(placements)

        # Extract cell sizes from cell_data if available
        cell_sizes_np = None
        if self.cell_data and 'cells' in self.cell_data:
            try:
                cell_sizes_np = np.array([
                    [c['width'], c['height']]
                    for c in self.cell_data['cells']
                ], dtype=float)
            except Exception:
                cell_sizes_np = None

        iterations_list = metrics.get('iterations', [])
        last_iteration  = iterations_list[-1] if iterations_list else 0

        # Feed physics visualizer — will auto-render
        self.physics_viz.set_placement_data(
            placements_np,
            cell_sizes_np=cell_sizes_np,
            iteration=last_iteration
        )

    def _on_placement_error(self, error_msg: str):
        self.log_console.log(f"[ERROR] {error_msg}")
        QMessageBox.critical(self, "Placement Error", error_msg)

    def _stop_placement(self):
        if self.placement_worker:
            self.placement_worker.stop()
            self.log_console.log("[MAIN] Placement stopped")

    # ──────────────────────────────────────────────────────────────────────────
    # Comparison
    # ──────────────────────────────────────────────────────────────────────────

    def _start_comparison(self):
        self.log_console.log("[MAIN] Starting QML vs Standard comparison...")

        self.comparison_worker = ComparisonWorkerThread()
        config = self.sidebar.get_placement_config()
        self.comparison_worker.set_placement_config(config)
        self.comparison_worker.set_cell_data(self._generate_demo_cells())
        self.comparison_worker.log_message.connect(self.log_console.log)
        self.comparison_worker.comparison_complete.connect(self._on_comparison_complete)
        self.comparison_worker.start()

    def _on_comparison_complete(self, results: dict):
        self.log_console.log(
            f"[MAIN] Comparison complete! "
            f"QML HPWL improvement: {results['hpwl_improvement_pct']:.1f}%"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # File / View / Tools actions
    # ──────────────────────────────────────────────────────────────────────────

    def _open_def(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open DEF", "", "DEF Files (*.def)")
        if path:
            self.log_console.log(f"[MAIN] Opened DEF: {path}")

    def _open_netlist(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Netlist", "", "Verilog Files (*.v)")
        if path:
            self.log_console.log(f"[MAIN] Opened netlist: {path}")

    def _save_config(self):
        self.log_console.log("[MAIN] Config saved")

    def _export_results(self):
        self.log_console.log("[MAIN] Results exported")

    def _run_full_flow(self):
        self.log_console.log("[MAIN] Running full OpenROAD flow...")

    def _run_standard_placer(self):
        self.log_console.log("[MAIN] Running standard placer...")

    def _run_demo(self):
        self.log_console.log("[MAIN] Running demo mode...")
        self._start_placement()

    def _toggle_log(self):
        self.log_console.setVisible(not self.log_console.isVisible())

    def _toggle_stats(self):
        self.stats_table.setVisible(not self.stats_table.isVisible())

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _openroad_settings(self):
        self.log_console.log("[MAIN] OpenROAD settings dialog")

    def _qml_settings(self):
        self.log_console.log("[MAIN] QML settings dialog")

    def _pdk_settings(self):
        self.log_console.log("[MAIN] PDK settings dialog")

    def _clear_history(self):
        self.log_console.log("[MAIN] History cleared")

    def _show_about(self):
        QMessageBox.information(
            self, "About QML·PLACE",
            "QML·PLACE v1.0.0\n\n"
            "Quantum Machine Learning Enhanced Global Placement\n"
            "for OpenROAD Sky130 Designs\n\n"
            "Design: CA234 | PDK: Sky130 HD | GPU: RTX 4060"
        )

    def _generate_report(self):
        self.log_console.log("[MAIN] Generating report...")

    def _save_def(self):
        self.log_console.log("[MAIN] DEF saved")

    # ──────────────────────────────────────────────────────────────────────────
    # Demo data
    # ──────────────────────────────────────────────────────────────────────────

    def _generate_demo_cells(self) -> dict:
        """
        Synthetic CA234-like cell data.
        Coordinates are in design units where 1 unit = 1 nm.
        Die size: 1000 µm × 1000 µm  →  1_000_000 × 1_000_000 units.
        """
        n_cells = 10_000
        rng     = np.random.default_rng(42)

        return {
            'cells': [
                {
                    'name':   f'cell_{i}',
                    'width':  int(rng.integers(460, 2000)),   # nm
                    'height': 2720,                            # nm  (standard row height)
                    'x':      int(rng.integers(0, 1_000_000)),
                    'y':      int(rng.integers(0, 1_000_000)),
                    'fixed':  i < 100,
                    'pins':   int(rng.integers(1, 10)),
                    'fanout': int(rng.integers(0, 20)),
                    'fanin':  int(rng.integers(0, 20)),
                }
                for i in range(n_cells)
            ],
            'nets': [
                {
                    'name': f'net_{i}',
                    'pins': [
                        {'cell': f'cell_{rng.integers(0, n_cells)}'}
                        for _ in range(int(rng.integers(2, 8)))
                    ]
                }
                for i in range(n_cells // 2)
            ],
            'die':   {'x0': 0, 'y0': 0, 'x1': 1_000_000, 'y1': 1_000_000},
            'rows':  [
                {'x': 0, 'y': i * 2720, 'width': 1_000_000, 'site': 'unithd'}
                for i in range(366)
            ],
            'units': 1000   # 1 unit = 1 nm
        }