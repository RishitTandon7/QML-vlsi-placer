"""
OpenROAD Report Parser: Extract timing, power, DRC, and area metrics from OpenROAD outputs
"""

import re
from typing import Dict, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class OpenROADReporter:
    """Parse and extract metrics from OpenROAD report files."""
    
    @staticmethod
    def parse_timing_report(report_path: str) -> Dict:
        """
        Parse timing report from OpenROAD.
        
        Returns dict with keys:
        - wns: Worst Negative Slack (float, in ns)
        - tns: Total Negative Slack (float, in ns)
        - worst_slack_path: Description of critical path (str)
        """
        result = {
            'wns': 0.0,
            'tns': 0.0,
            'worst_slack_path': '',
            'num_paths': 0,
            'error': None
        }
        
        try:
            with open(report_path, 'r') as f:
                content = f.read()
            
            # Parse WNS
            wns_match = re.search(r'WNS\s*=\s*([-\d.]+)', content)
            if wns_match:
                result['wns'] = float(wns_match.group(1))
            
            # Parse TNS
            tns_match = re.search(r'TNS\s*=\s*([-\d.]+)', content)
            if tns_match:
                result['tns'] = float(tns_match.group(1))
            
            # Parse number of violating paths
            paths_match = re.search(r'([0-9]+)\s+paths?', content, re.IGNORECASE)
            if paths_match:
                result['num_paths'] = int(paths_match.group(1))
            
            logger.info(f"[REPORTER] Timing: WNS={result['wns']:.3f}ns, TNS={result['tns']:.3f}ns")
            
        except FileNotFoundError:
            result['error'] = f"Report file not found: {report_path}"
            logger.warning(f"[REPORTER] {result['error']}")
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"[REPORTER] Error parsing timing report: {e}")
        
        return result
    
    @staticmethod
    def parse_power_report(report_path: str) -> Dict:
        """
        Parse power report from OpenROAD.
        
        Returns dict with:
        - total_mw: Total power in mW
        - dynamic_mw: Dynamic power in mW
        - static_mw: Static (leakage) power in mW
        """
        result = {
            'total_mw': 0.0,
            'dynamic_mw': 0.0,
            'static_mw': 0.0,
            'error': None
        }
        
        try:
            with open(report_path, 'r') as f:
                content = f.read()
            
            # Parse total power
            total_match = re.search(r'Total\s*:\s*([\d.]+)\s*mW', content)
            if total_match:
                result['total_mw'] = float(total_match.group(1))
            
            # Parse dynamic power
            dynamic_match = re.search(r'Dynamic\s*:\s*([\d.]+)\s*mW', content)
            if dynamic_match:
                result['dynamic_mw'] = float(dynamic_match.group(1))
            
            # Parse static power
            static_match = re.search(r'Static|Leakage\s*:\s*([\d.]+)\s*mW', content)
            if static_match:
                result['static_mw'] = float(static_match.group(1))
            
            logger.info(f"[REPORTER] Power: Total={result['total_mw']:.3f}mW, "
                       f"Dynamic={result['dynamic_mw']:.3f}mW, Static={result['static_mw']:.3f}mW")
            
        except FileNotFoundError:
            result['error'] = f"Report file not found: {report_path}"
            logger.warning(f"[REPORTER] {result['error']}")
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"[REPORTER] Error parsing power report: {e}")
        
        return result
    
    @staticmethod
    def parse_drc_report(report_path: str) -> Dict:
        """
        Parse DRC report from OpenROAD.
        
        Returns dict with:
        - violation_count: Total number of violations
        - violations: List of violation descriptions
        """
        result = {
            'violation_count': 0,
            'violations': [],
            'error': None
        }
        
        try:
            with open(report_path, 'r') as f:
                lines = f.readlines()
            
            violations = []
            for line in lines:
                # Skip comments and empty lines
                if line.startswith('#') or line.strip() == '':
                    continue
                
                # Match violation patterns
                if 'violation' in line.lower() or 'error' in line.lower():
                    violations.append(line.strip())
            
            result['violation_count'] = len(violations)
            result['violations'] = violations
            
            logger.info(f"[REPORTER] DRC: {result['violation_count']} violations")
            
        except FileNotFoundError:
            result['error'] = f"Report file not found: {report_path}"
            logger.warning(f"[REPORTER] {result['error']}")
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"[REPORTER] Error parsing DRC report: {e}")
        
        return result
    
    @staticmethod
    def parse_area_report(report_path: str) -> Dict:
        """
        Parse area and utilization report.
        
        Returns dict with:
        - die_area_um2: Die area in µm²
        - cell_area_um2: Total cell area in µm²
        - util_pct: Cell utilization percentage (0-100)
        """
        result = {
            'die_area_um2': 0.0,
            'cell_area_um2': 0.0,
            'util_pct': 0.0,
            'error': None
        }
        
        try:
            with open(report_path, 'r') as f:
                content = f.read()
            
            # Parse die area
            die_match = re.search(r'Die\s*area\s*[:=]?\s*([\d.]+)\s*', content)
            if die_match:
                result['die_area_um2'] = float(die_match.group(1))
            
            # Parse cell area
            cell_match = re.search(r'Cell\s*area\s*[:=]?\s*([\d.]+)\s*', content)
            if cell_match:
                result['cell_area_um2'] = float(cell_match.group(1))
            
            # Parse utilization
            util_match = re.search(r'Utilization\s*[:=]?\s*([\d.]+)\s*%', content)
            if util_match:
                result['util_pct'] = float(util_match.group(1))
            elif result['die_area_um2'] > 0:
                result['util_pct'] = 100.0 * result['cell_area_um2'] / result['die_area_um2']
            
            logger.info(f"[REPORTER] Area: Die={result['die_area_um2']:.1f}µm², "
                       f"Cells={result['cell_area_um2']:.1f}µm², "
                       f"Util={result['util_pct']:.1f}%")
            
        except FileNotFoundError:
            result['error'] = f"Report file not found: {report_path}"
            logger.warning(f"[REPORTER] {result['error']}")
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"[REPORTER] Error parsing area report: {e}")
        
        return result
    
    @staticmethod
    def parse_placement_metrics(report_path: str) -> Dict:
        """Parse placement quality metrics (congestion, overflow, etc)."""
        result = {
            'overflow': 0.0,
            'congestion': 0.0,
            'density': 0.0,
            'error': None
        }
        
        try:
            with open(report_path, 'r') as f:
                content = f.read()
            
            # Parse overflow
            overflow_match = re.search(r'Overflow\s*[:=]?\s*([\d.]+)\s*%?', content)
            if overflow_match:
                result['overflow'] = float(overflow_match.group(1))
            
            # Parse congestion
            cong_match = re.search(r'Congestion\s*[:=]?\s*([\d.]+)\s*%?', content)
            if cong_match:
                result['congestion'] = float(cong_match.group(1))
            
            # Parse density
            dens_match = re.search(r'Density\s*[:=]?\s*([\d.]+)\s*%?', content)
            if dens_match:
                result['density'] = float(dens_match.group(1))
            
            logger.info(f"[REPORTER] Placement: Overflow={result['overflow']:.2f}%, "
                       f"Congestion={result['congestion']:.2f}%, "
                       f"Density={result['density']:.2f}%")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"[REPORTER] Error parsing placement metrics: {e}")
        
        return result
    
    @staticmethod
    def generate_summary(timing: Dict, power: Dict, drc: Dict, area: Dict) -> str:
        """Generate summary report from parsed metrics."""
        summary = f"""
═══════════════════════════════════════════════════════════
 PLACEMENT & OPTIMIZATION REPORT
═══════════════════════════════════════════════════════════

TIMING:
  WNS (Worst Negative Slack):    {timing.get('wns', 0.0):.3f} ns
  TNS (Total Negative Slack):    {timing.get('tns', 0.0):.3f} ns
  Violating Paths:               {timing.get('num_paths', 0)}

POWER:
  Total Power:                   {power.get('total_mw', 0.0):.3f} mW
  Dynamic Power:                 {power.get('dynamic_mw', 0.0):.3f} mW
  Static Power (Leakage):        {power.get('static_mw', 0.0):.3f} mW

DRC VIOLATIONS:
  Total Violations:              {drc.get('violation_count', 0)}

AREA & UTILIZATION:
  Die Area:                      {area.get('die_area_um2', 0.0):.1f} µm²
  Total Cell Area:               {area.get('cell_area_um2', 0.0):.1f} µm²
  Utilization:                   {area.get('util_pct', 0.0):.1f} %

═══════════════════════════════════════════════════════════
"""
        return summary
