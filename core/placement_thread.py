"""
Placement Thread: QThread worker for asynchronous placement computation
Emits signals for UI updates during long-running operations
"""

from PyQt6.QtCore import QThread, pyqtSignal
import logging
from typing import Optional, Dict
import sys
import traceback

logger = logging.getLogger(__name__)


class PlacementWorkerThread(QThread):
    """Worker thread for placement computation."""
    
    # Signals
    stage_changed = pyqtSignal(str, int)  # (stage_name, percentage)
    iteration_updated = pyqtSignal(int, int, float, float, int)  # (current_iter, total_iter, hpwl, overflow, eta_seconds)
    placement_complete = pyqtSignal(object, dict)  # (placements, metrics)
    error_occurred = pyqtSignal(str)  # (error_message)
    log_message = pyqtSignal(str)  # (log_message)
    
    def __init__(self):
        super().__init__()
        self.placement_config = {}
        self.cell_data = None
        self.qml_model = None
        self.is_running = False
    
    def run(self):
        """Execute placement in worker thread."""
        self.is_running = True
        
        try:
            self.log_message.emit("[PLACEMENT_THREAD] Starting placement worker")
            
            # Stage 1: Initialize
            self.stage_changed.emit("Initializing", 5)
            
            if self.cell_data is None:
                raise ValueError("No cell data provided")
            
            # Stage 2: Feature extraction
            self.stage_changed.emit("Feature Extraction", 15)
            self.log_message.emit("[PLACEMENT_THREAD] Extracting Sky130 features...")
            
            from core.openroad_bridge import sky130_feature_extraction
            features = sky130_feature_extraction(self.cell_data)
            self.log_message.emit(f"[PLACEMENT_THREAD] Extracted {features.shape[0]} cells with {features.shape[1]} features")
            
            # Stage 3: QML Inference (if model provided)
            if self.qml_model is not None:
                self.stage_changed.emit("QML Inference", 25)
                self.log_message.emit("[PLACEMENT_THREAD] Running QML model...")
            
            # Stage 4: Global Placement
            self.stage_changed.emit("Global Placement", 35)
            self.log_message.emit("[PLACEMENT_THREAD] Starting placement optimization...")
            
            from core.global_placement_engine import GlobalPlacementEngine
            
            engine = GlobalPlacementEngine(self.placement_config.get('config_path', 'configs/ca234_sky130.json'))
            
            # Define callback for iteration updates
            def iter_callback(current, total, hpwl, overflow, eta_seconds=0):
                progress = 35 + int(45 * current / total)  # 35-80% for placement
                self.stage_changed.emit(f"Global Placement ({current}/{total})", progress)
                if eta_seconds == 0 and current > 0:
                    eta_seconds = 1  # Set a minimum ETA of 1 second for the first iteration
                self.iteration_updated.emit(current, total, hpwl, overflow, eta_seconds)
            
            placements, metrics = engine.run_placement(
                self.cell_data,
                qml_model=self.qml_model,
                target_density=self.placement_config.get('target_density', 0.55),
                iterations=self.placement_config.get('iterations', 2000),
                learning_rate=self.placement_config.get('learning_rate', 0.01),
                callback=iter_callback
            )
            
            if not self.is_running:
                self.log_message.emit("[PLACEMENT_THREAD] Placement cancelled")
                return
            
            # Stage 5: Legalization
            self.stage_changed.emit("Legalization", 80)
            self.log_message.emit("[PLACEMENT_THREAD] Legalizing placement...")
            
            # Stage 6: Write Results
            self.stage_changed.emit("Writing Results", 95)
            self.log_message.emit("[PLACEMENT_THREAD] Saving placement results...")
            
            # Final stage
            self.stage_changed.emit("Complete", 100)
            self.log_message.emit("[PLACEMENT_THREAD] Placement complete!")
            
            # Emit result
            self.placement_complete.emit(placements, metrics)
        
        except Exception as e:
            logger.error(f"[PLACEMENT_THREAD] Error: {e}")
            self.log_message.emit(f"[ERROR] {str(e)}")
            self.error_occurred.emit(f"Placement failed: {str(e)}\n{traceback.format_exc()}")
        
        finally:
            self.is_running = False
    
    def stop(self):
        """Request thread stop."""
        self.is_running = False
        self.wait()
    
    def set_placement_config(self, config: Dict):
        """Set placement configuration."""
        self.placement_config = config
    
    def set_cell_data(self, cell_data: Dict):
        """Set cell data to place."""
        self.cell_data = cell_data
    
    def set_qml_model(self, model):
        """Set QML model for initialization."""
        self.qml_model = model


class ComparisonWorkerThread(QThread):
    """Worker thread for running QML vs Standard placement comparison."""
    
    qml_complete = pyqtSignal(object, dict)  # (placements, metrics)
    standard_complete = pyqtSignal(object, dict)  # (placements, metrics)
    comparison_complete = pyqtSignal(dict)  # (comparison_results)
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.placement_config = {}
        self.cell_data = None
        self.qml_model = None
        self.is_running = False
    
    def run(self):
        """Execute both placements and compare."""
        self.is_running = True
        
        try:
            self.log_message.emit("[COMPARISON] Starting QML vs Standard comparison")
            
            # Run QML placement
            self.log_message.emit("[COMPARISON] Running QML placement...")
            from core.global_placement_engine import GlobalPlacementEngine
            
            engine = GlobalPlacementEngine()
            qml_placements, qml_metrics = engine.run_placement(
                self.cell_data,
                qml_model=self.qml_model,
                target_density=self.placement_config.get('target_density', 0.55),
                iterations=self.placement_config.get('iterations', 2000)
            )
            
            if not self.is_running:
                return
            
            self.qml_complete.emit(qml_placements, qml_metrics)
            self.log_message.emit("[COMPARISON] QML placement complete")
            
            # Run Standard placement
            self.log_message.emit("[COMPARISON] Running Standard (RePlAce) placement...")
            standard_placements, standard_metrics = engine.run_placement(
                self.cell_data,
                qml_model=None,  # No QML model for standard
                target_density=self.placement_config.get('target_density', 0.55),
                iterations=self.placement_config.get('iterations', 2000)
            )
            
            if not self.is_running:
                return
            
            self.standard_complete.emit(standard_placements, standard_metrics)
            self.log_message.emit("[COMPARISON] Standard placement complete")
            
            # Compare results
            comparison = {
                'qml_hpwl': qml_metrics.get('final_hpwl', 0),
                'standard_hpwl': standard_metrics.get('final_hpwl', 0),
                'hpwl_improvement_pct': 100 * (standard_metrics.get('final_hpwl', 1) - qml_metrics.get('final_hpwl', 0)) / standard_metrics.get('final_hpwl', 1),
                'qml_time_s': qml_metrics.get('total_time', 0),
                'standard_time_s': standard_metrics.get('total_time', 0),
                'speedup': standard_metrics.get('total_time', 1) / max(0.001, qml_metrics.get('total_time', 1))
            }
            
            self.comparison_complete.emit(comparison)
            self.log_message.emit(f"[COMPARISON] Results: QML HPWL={comparison['qml_hpwl']:.2f}µm, "
                                 f"Standard HPWL={comparison['standard_hpwl']:.2f}µm, "
                                 f"Improvement={comparison['hpwl_improvement_pct']:.1f}%")
        
        except Exception as e:
            self.log_message.emit(f"[ERROR] {str(e)}")
            self.error_occurred.emit(str(e))
        
        finally:
            self.is_running = False
    
    def stop(self):
        """Request thread stop."""
        self.is_running = False
        self.wait()
    
    def set_placement_config(self, config: Dict):
        self.placement_config = config
    
    def set_cell_data(self, cell_data: Dict):
        self.cell_data = cell_data
    
    def set_qml_model(self, model):
        self.qml_model = model
