"""
GPU Monitoring for NVIDIA GPUs (RTX 4060)
Tracks memory, utilization, temperature, and power
"""

import logging
from typing import Dict, Optional
import threading
import time

logger = logging.getLogger(__name__)


class GPUMonitor:
    """Monitor NVIDIA GPU metrics in real-time."""
    
    def __init__(self, device_id: int = 0):
        """
        Initialize GPU monitor.
        
        Args:
            device_id: CUDA device ID (0 for single GPU)
        """
        self.device_id = device_id
        self.pynvml_available = False
        self.current_metrics = {
            'available': False,
            'device_name': 'NVIDIA GPU',
            'utilization': 0.0,
            'vram_used_mb': 0,
            'vram_total_mb': 0,
            'vram_percent': 0.0,
            'temperature_c': 0.0,
            'power_w': 0.0,
            'max_power_w': 0.0,
            'error': None
        }
        
        self._initialize_nvml()
        self._monitoring = False
        self._monitor_thread = None
    
    def _initialize_nvml(self):
        """Initialize NVIDIA Management Library."""
        try:
            import pynvml
            pynvml.nvmlInit()
            self.pynvml_available = True
            
            # Get device info
            try:
                gpu_count = pynvml.nvmlDeviceGetCount()
                if self.device_id < gpu_count:
                    self.device = pynvml.nvmlDeviceGetHandleByIndex(self.device_id)
                    device_name = pynvml.nvmlDeviceGetName(self.device)
                    # Handle both bytes and str returns (different nvidia-ml-py versions)
                    if isinstance(device_name, bytes):
                        device_name = device_name.decode('utf-8')
                    self.current_metrics['device_name'] = device_name
                    self.current_metrics['available'] = True
                    
                    # Get max power limit
                    try:
                        max_power = pynvml.nvmlDeviceGetPowerManagementLimit(self.device) / 1000.0
                        self.current_metrics['max_power_w'] = max_power
                    except:
                        pass
                    
                    logger.info(f"[GPU_MONITOR] Initialized: {self.current_metrics['device_name']}")
                else:
                    logger.warning(f"[GPU_MONITOR] Device {self.device_id} not found. Found {gpu_count} devices.")
                    self.current_metrics['error'] = f"Device {self.device_id} not found"
            except Exception as e:
                logger.warning(f"[GPU_MONITOR] Could not initialize device: {e}")
                self.current_metrics['error'] = str(e)
        
        except ImportError:
            logger.warning("[GPU_MONITOR] pynvml not available. GPU monitoring disabled.")
            self.current_metrics['error'] = "pynvml not installed"
        except Exception as e:
            logger.warning(f"[GPU_MONITOR] Initialization error: {e}")
            self.current_metrics['error'] = str(e)
    
    def get_metrics(self) -> Dict:
        """Get current GPU metrics."""
        if not self.pynvml_available:
            return self.current_metrics
        
        try:
            import pynvml
            
            if self.current_metrics['available']:
                # GPU Utilization
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(self.device)
                    self.current_metrics['utilization'] = util.gpu
                except:
                    pass
                
                # VRAM
                try:
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(self.device)
                    self.current_metrics['vram_used_mb'] = mem_info.used // (1024 * 1024)
                    self.current_metrics['vram_total_mb'] = mem_info.total // (1024 * 1024)
                    self.current_metrics['vram_percent'] = 100.0 * mem_info.used / mem_info.total
                except:
                    pass
                
                # Temperature
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(self.device, 0)
                    self.current_metrics['temperature_c'] = temp
                except:
                    pass
                
                # Power
                try:
                    power_mw = pynvml.nvmlDeviceGetPowerUsage(self.device)
                    self.current_metrics['power_w'] = power_mw / 1000.0
                except:
                    pass
        
        except Exception as e:
            logger.debug(f"[GPU_MONITOR] Error reading metrics: {e}")
        
        return self.current_metrics.copy()
    
    def start_monitoring(self, interval: float = 1.0):
        """Start background monitoring thread."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info(f"[GPU_MONITOR] Started monitoring at {interval}s intervals")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("[GPU_MONITOR] Stopped monitoring")
    
    def _monitor_loop(self, interval: float):
        """Background monitoring loop."""
        while self._monitoring:
            self.get_metrics()
            time.sleep(interval)
    
    def get_status_string(self) -> str:
        """Get human-readable status string."""
        metrics = self.get_metrics()
        
        if not metrics['available']:
            return "GPU: Not available"
        
        return (
            f"GPU: {metrics['device_name']} | "
            f"Util: {metrics['utilization']:.1f}% | "
            f"VRAM: {metrics['vram_used_mb']}/{metrics['vram_total_mb']}MB ({metrics['vram_percent']:.1f}%) | "
            f"Temp: {metrics['temperature_c']:.1f}°C | "
            f"Power: {metrics['power_w']:.1f}W"
        )
    
    def check_memory_available(self, required_mb: int = 2048) -> bool:
        """Check if sufficient GPU memory is available."""
        metrics = self.get_metrics()
        available_mb = metrics['vram_total_mb'] - metrics['vram_used_mb']
        return available_mb >= required_mb
    
    def get_memory_status(self) -> Dict:
        """Get detailed memory status."""
        metrics = self.get_metrics()
        return {
            'used_mb': metrics['vram_used_mb'],
            'total_mb': metrics['vram_total_mb'],
            'available_mb': metrics['vram_total_mb'] - metrics['vram_used_mb'],
            'percent_used': metrics['vram_percent']
        }
