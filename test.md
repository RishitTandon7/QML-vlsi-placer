# QML·PLACE Test Plan
# Design: CA234 | PDK: Sky130 HD | GPU: RTX 4060

## 1. Environment Tests

### 1.1 Docker Build
```bash
docker build -t qml-or-sky130 .
```
Expected: No errors, all dependencies installed, global placement engine compiled

### 1.2 OpenROAD Version Check
```bash
docker run qml-or-sky130 openroad -version
```
Expected: OpenROAD vX.X.X (recent version)

### 1.3 Sky130 PDK Check
```bash
docker run qml-or-sky130 ls /opt/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/
```
Expected: sky130_fd_sc_hd.lef present

### 1.4 CA234 Design Check
```bash
docker run qml-or-sky130 ls /workspace/designs/CA234/
```
Expected: CA234.v, CA234.sdc, CA234.def all present

### 1.5 GUI Launch
```bash
docker-compose up
# Open http://localhost:6080
```
Expected: PyQt6 window visible within 20s, noVNC shows QML·PLACE UI

## 2. OpenROAD Bridge Tests

### 2.1 LEF/DEF Read
```python
from core.openroad_bridge import load_openroad_design
db = load_openroad_design(
  lef=['sky130_fd_sc_hd.tlef','sky130_fd_sc_hd.lef'],
  def_file='designs/CA234/CA234.def')
print('Cells:', db.getChip().getBlock().getInsts().size())
```
Expected: Cells: > 0 (typically 10,000+)

### 2.2 Feature Extraction
```python
from core.openroad_bridge import extract_from_openroad, sky130_feature_extraction
data = extract_from_openroad(db)
feats = sky130_feature_extraction(data)
assert feats.shape[1] == 8  # 8 features
assert np.all(np.isfinite(feats))
```
Expected: Features shape (N, 8), all values finite

### 2.3 Coordinate Conversion
Verify DBU ↔ µm conversions consistent with Sky130 (1000 DBU = 1 µm)

## 3. Global Placement Engine Tests

### 3.1 Engine Initialization
```python
from core.global_placement_engine import GlobalPlacementEngine
engine = GlobalPlacementEngine('configs/ca234_sky130.json')
assert engine.config['benchmark'] == 'CA234'
```
Expected: Config loaded, no errors

### 3.2 Placement Execution
```python
placements, metrics = engine.run_placement(
  cell_data,
  target_density=0.55,
  iterations=2000)
assert placements.shape[0] > 0
```
Expected: Placements generated, metrics computed

### 3.3 HPWL Improvement
Run QML vs Standard placement on CA234
Target: QML HPWL ≤ standard HPWL (≥ 0% improvement)
Stretch target: ≥ 8% improvement

### 3.4 Density Constraint
Verify final overflow < 1% at target_density=0.55

## 4. Sky130-Specific Tests

### 4.1 Row Alignment
All cell Y coordinates must be multiples of 2720 DBU (2.72 µm row height)

### 4.2 Site Width Alignment
All cell X coordinates must be multiples of 460 DBU (0.46 µm site)

### 4.3 Die Boundary Constraints
No cell placed outside die area from CA234.def

### 4.4 Power Net Exclusion
VDD/VSS nets excluded from feature fanout/fanin counts

## 5. Timing Tests (OpenROAD Reports)

### 5.1 WNS After Placement
Target: WNS > -0.5ns (better than standard placer)

### 5.2 TNS Improvement
Target: TNS less negative vs standard placer

### 5.3 DRC Violations
Target: 0 placement DRC violations at density=0.55

## 6. GUI Tests

### 6.1 Load CA234 DEF
Click "Load CA234 DEF" → select CA234.def
Expected: Canvas populates, cell count shown

### 6.2 Sky130 Row Grid
After loading: horizontal gray lines visible every 2.72 µm at high zoom

### 6.3 QML Placement Run
- Set target density to 0.55
- Set QML: 8 qubits, 4 layers
- Click "▶ RUN QML PLACEMENT"
Expected: Progress bar animates through 8 stages, completion in < 8 min

### 6.4 Real-time Charts
- HPWL chart shows wirelength decreasing
- Density overflow chart shows convergence
- QML loss chart (log scale) decreasing
- GPU utilization RTX 4060 peaks ~85%

### 6.5 Stats Table
After run: new row appears with metrics
- Placer: "QML" badge (cyan)
- HPWL: 38.42 µm (green if improvement)
- WNS: ±0.12 ns
- Status: "DONE" (green background)

### 6.6 GPU Panel
- Device: NVIDIA RTX 4060
- Utilization: peaks ~87%
- VRAM: peaks ~4.2 GB (within 6 GB)
- Temperature: stays < 75°C
- Power: peaks ~130W

### 6.7 Comparison Mode
- Enable "Run standard placer for comparison"
- Run placement
- Both QML and Standard results in table
- Comparison shows improvement percentage

## 7. Performance Benchmarks

| Metric | Target | Notes |
|--------|--------|-------|
| Full QML flow (end-to-end) | < 8 min | CA234 on RTX 4060 |
| QML inference only | < 10 sec | 10k cells |
| Peak VRAM | < 6 GB | 2 GB headroom available |
| OpenROAD LEF/DEF read | < 30 sec | - |
| Canvas render initial | < 2 sec | 10k cells |
| Table sort 100 rows | < 200 ms | - |
| GUI response | < 500 ms | Any button click |

## 8. Error Handling Tests

### 8.1 Missing PDK Path
Action: Set wrong PDK path, try to load LEF
Expected: Error message "PDK not found at <path>"

### 8.2 Missing CA234 Design Files
Action: Try to run placement without CA234.def
Expected: FAILED row in table, error logged

### 8.3 Global Placement Engine OOM
Action: Manually increase cell count beyond VRAM capacity
Expected: "Out of memory" error, graceful fallback

### 8.4 OpenROAD Not Found
Action: Set invalid OpenROAD path
Expected: Error message, placement button disabled

### 8.5 QML Model Initialization Failure
Action: Corrupt checkpoint file
Expected: Falls back to random initialization, logs warning

## 9. Smoke Test Script

```bash
#!/bin/bash
set -e

echo "[SMOKE] Building Docker image..."
docker build -t qml-or-sky130 . && echo "✓ BUILD OK"

echo "[SMOKE] Launching container..."
docker-compose up -d && sleep 25

echo "[SMOKE] Checking VNC..."
curl -sf http://localhost:6080/ | grep -q "noVNC" && echo "✓ VNC OK"

echo "[SMOKE] Checking OpenROAD..."
docker exec $(docker ps -q) openroad -version && echo "✓ OR OK"

echo "[SMOKE] Checking Sky130 PDK..."
docker exec $(docker ps -q) ls /opt/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/*.lef && echo "✓ PDK OK"

echo "[SMOKE] Checking CA234 design..."
docker exec $(docker ps -q) ls /workspace/designs/CA234/{CA234.v,CA234.sdc,CA234.def} && echo "✓ DESIGN OK"

echo "[SMOKE] Testing QML model..."
docker exec $(docker ps -q) python -c "
from core.qml_model import QMLPlacementModel
import torch
m = QMLPlacementModel(8, 4)
x = torch.rand(4, 8)
y = m.decoder(m.pre_encoder(x))
assert y.shape == torch.Size([4, 2])
print('✓ QML OK')"

echo "[SMOKE] Checking CUDA..."
docker exec $(docker ps -q) python -c "
import torch
assert torch.cuda.is_available()
print('✓ GPU:', torch.cuda.get_device_name(0))"

echo "[SMOKE] Checking SQLite..."
docker exec $(docker ps -q) python -c "
from core.stats_store import StatsStore
s = StatsStore()
rows = s.get_all(limit=1)
print('✓ DB OK')"

echo "[SMOKE] Cleaning up..."
docker-compose down && echo "✓ CLEANUP OK"

echo ""
echo "════════════════════════════════════════════════════════════"
echo " ALL SMOKE TESTS PASSED ✓"
echo "════════════════════════════════════════════════════════════"
```

## 10. Launch Instructions

### Development (with debugging)
```bash
docker-compose up --build -d
docker logs -f qml-placer-container
```

### Production (clean run)
```bash
docker-compose up -d
# Open http://localhost:6080
# VNC password: qmlplace
```

### Shutdown
```bash
docker-compose down
```

## 11. Pass/Fail Criteria

**PASS**: All smoke tests pass + QML HPWL ≥ baseline (0% improvement minimum)

**CONDITIONAL PASS**: Smoke tests pass, QML slower but correct

**FAIL**: Build errors, runtime crashes, or QML unable to place cells

---

**Version**: 1.0.0  
**Last Updated**: 2026-05-06  
**Status**: Ready for testing
