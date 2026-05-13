"""
Statistics Store: SQLite database for placement run history and metrics
Schema optimized for CA234 Sky130 placement runs
"""

import sqlite3
import json
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class StatsStore:
    """SQLite database for placement statistics and run history."""
    
    DB_FILE = "placement_stats.db"
    
    def __init__(self, db_path: str = DB_FILE):
        """
        Initialize stats store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Main runs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                placer TEXT NOT NULL,
                design_name TEXT DEFAULT 'CA234',
                pdk TEXT DEFAULT 'Sky130',
                
                -- QML Config
                qml_enabled INTEGER DEFAULT 1,
                qml_n_qubits INTEGER DEFAULT 8,
                qml_n_layers INTEGER DEFAULT 4,
                qml_diff_method TEXT DEFAULT 'parameter-shift',
                
                -- Placement Config
                optimizer TEXT DEFAULT 'nesterov',
                target_density REAL DEFAULT 0.55,
                iterations INTEGER DEFAULT 2000,
                learning_rate REAL DEFAULT 0.01,
                
                -- Timing Metrics
                wns_ns REAL DEFAULT NULL,
                tns_ns REAL DEFAULT NULL,
                path_violations INTEGER DEFAULT 0,
                
                -- Wirelength
                hpwl_um REAL DEFAULT NULL,
                hpwl_improvement_pct REAL DEFAULT NULL,
                
                -- Density
                overflow_pct REAL DEFAULT NULL,
                congestion_pct REAL DEFAULT NULL,
                utilization_pct REAL DEFAULT NULL,
                
                -- Performance
                placement_time_s REAL DEFAULT NULL,
                qml_time_s REAL DEFAULT NULL,
                legalize_time_s REAL DEFAULT NULL,
                total_time_s REAL DEFAULT NULL,
                speedup_vs_standard REAL DEFAULT NULL,
                
                -- Power
                total_power_mw REAL DEFAULT NULL,
                dynamic_power_mw REAL DEFAULT NULL,
                static_power_mw REAL DEFAULT NULL,
                
                -- GPU
                peak_vram_gb REAL DEFAULT NULL,
                avg_gpu_util_pct REAL DEFAULT NULL,
                peak_temp_c REAL DEFAULT NULL,
                avg_power_w REAL DEFAULT NULL,
                
                -- Quality
                drc_violations INTEGER DEFAULT 0,
                placement_violations INTEGER DEFAULT 0,
                
                -- Status
                status TEXT DEFAULT 'DONE',
                error_message TEXT DEFAULT NULL,
                notes TEXT DEFAULT NULL,
                
                UNIQUE(timestamp, placer)
            )
        ''')
        
        # Comparison table (QML vs Standard)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comparisons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                qml_run_id INTEGER,
                standard_run_id INTEGER,
                hpwl_delta_pct REAL,
                time_delta_s REAL,
                wns_delta_ns REAL,
                tns_delta_ns REAL,
                FOREIGN KEY(qml_run_id) REFERENCES runs(id),
                FOREIGN KEY(standard_run_id) REFERENCES runs(id)
            )
        ''')
        
        # Convergence history (per iteration)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS convergence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                iteration INTEGER,
                hpwl_um REAL,
                overflow_pct REAL,
                loss REAL,
                timestamp REAL,
                FOREIGN KEY(run_id) REFERENCES runs(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"[STATS_STORE] Initialized database: {self.db_path}")
    
    def add_run(self, run_data: Dict) -> int:
        """
        Add a new placement run record.
        
        Returns:
            Run ID (auto-increment)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Ensure timestamp
        if 'timestamp' not in run_data:
            run_data['timestamp'] = datetime.now().isoformat()
        
        # Prepare data
        columns = ', '.join(run_data.keys())
        placeholders = ', '.join(['?' for _ in run_data])
        values = tuple(run_data.values())
        
        cursor.execute(f'''
            INSERT INTO runs ({columns})
            VALUES ({placeholders})
        ''', values)
        
        run_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"[STATS_STORE] Added run {run_id}: {run_data.get('placer', '?')}")
        return run_id
    
    def update_run(self, run_id: int, updates: Dict):
        """Update an existing run record."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        set_clause = ', '.join([f'{k}=?' for k in updates.keys()])
        values = tuple(list(updates.values()) + [run_id])
        
        cursor.execute(f'UPDATE runs SET {set_clause} WHERE id=?', values)
        conn.commit()
        conn.close()
    
    def add_convergence_point(self, run_id: int, iteration: int, 
                             hpwl: float, overflow: float, loss: float):
        """Record a single iteration's metrics."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        timestamp = time.time()
        cursor.execute('''
            INSERT INTO convergence (run_id, iteration, hpwl_um, overflow_pct, loss, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (run_id, iteration, hpwl, overflow, loss, timestamp))
        
        conn.commit()
        conn.close()
    
    def get_run(self, run_id: int) -> Optional[Dict]:
        """Retrieve a single run record."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM runs WHERE id=?', (run_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Retrieve all run records (paginated)."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM runs
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_qml_runs(self, limit: int = 50) -> List[Dict]:
        """Get all QML placement runs."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM runs WHERE placer='QML'
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_best_qml_run(self) -> Optional[Dict]:
        """Get QML run with best HPWL."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM runs WHERE placer='QML' AND status='DONE'
            ORDER BY hpwl_um ASC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_stats_summary(self) -> Dict:
        """Get overall statistics summary."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        summary = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'qml_runs': 0,
            'standard_runs': 0,
            'avg_hpwl_um': None,
            'best_hpwl_um': None,
            'avg_wns_ns': None,
            'avg_speedup': None
        }
        
        try:
            # Total runs
            cursor.execute('SELECT COUNT(*) as count FROM runs')
            summary['total_runs'] = cursor.fetchone()[0]
            
            # Status breakdown
            cursor.execute("SELECT COUNT(*) as count FROM runs WHERE status='DONE'")
            summary['successful_runs'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) as count FROM runs WHERE status='FAILED'")
            summary['failed_runs'] = cursor.fetchone()[0]
            
            # Placer breakdown
            cursor.execute("SELECT COUNT(*) as count FROM runs WHERE placer='QML'")
            summary['qml_runs'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) as count FROM runs WHERE placer='Standard'")
            summary['standard_runs'] = cursor.fetchone()[0]
            
            # Metrics
            cursor.execute("SELECT AVG(hpwl_um), MIN(hpwl_um) FROM runs WHERE status='DONE'")
            result = cursor.fetchone()
            summary['avg_hpwl_um'] = result[0]
            summary['best_hpwl_um'] = result[1]
            
            cursor.execute("SELECT AVG(wns_ns) FROM runs WHERE status='DONE'")
            summary['avg_wns_ns'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(speedup_vs_standard) FROM runs WHERE placer='QML' AND status='DONE'")
            summary['avg_speedup'] = cursor.fetchone()[0]
        
        except Exception as e:
            logger.error(f"[STATS_STORE] Error computing summary: {e}")
        
        finally:
            conn.close()
        
        return summary
    
    def export_csv(self, output_path: str):
        """Export all runs to CSV file."""
        import csv
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM runs ORDER BY timestamp DESC')
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            logger.warning("[STATS_STORE] No runs to export")
            return
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        
        logger.info(f"[STATS_STORE] Exported {len(rows)} runs to {output_path}")


# Demo data insertion
def insert_demo_data():
    """Insert 8 demo CA234 Sky130 runs for testing GUI."""
    import time
    store = StatsStore()
    
    demo_runs = [
        {
            'timestamp': datetime(2026, 5, 6, 10, 0).isoformat(),
            'placer': 'QML',
            'design_name': 'CA234',
            'pdk': 'Sky130',
            'qml_n_qubits': 8,
            'qml_n_layers': 4,
            'target_density': 0.55,
            'hpwl_um': 38.42e6,
            'hpwl_improvement_pct': 12.4,
            'wns_ns': -0.12,
            'tns_ns': -0.34,
            'overflow_pct': 0.21,
            'utilization_pct': 55.0,
            'placement_time_s': 258,
            'qml_time_s': 45,
            'total_time_s': 258,
            'speedup_vs_standard': 1.31,
            'peak_vram_gb': 4.2,
            'avg_gpu_util_pct': 87.3,
            'peak_temp_c': 72,
            'drc_violations': 0,
            'status': 'DONE'
        },
        {
            'timestamp': datetime(2026, 5, 6, 9, 0).isoformat(),
            'placer': 'Standard',
            'design_name': 'CA234',
            'pdk': 'Sky130',
            'target_density': 0.55,
            'hpwl_um': 43.87e6,
            'wns_ns': -0.31,
            'tns_ns': -1.12,
            'overflow_pct': 0.18,
            'utilization_pct': 55.0,
            'placement_time_s': 231,
            'total_time_s': 231,
            'speedup_vs_standard': 1.00,
            'peak_vram_gb': 2.1,
            'drc_violations': 0,
            'status': 'DONE'
        }
    ]
    
    # Add more demo runs
    for i, base_run in enumerate(demo_runs[:2]):
        if i > 0:
            break
        store.add_run(base_run)
    
    logger.info(f"[STATS_STORE] Inserted {len(demo_runs)} demo runs")
