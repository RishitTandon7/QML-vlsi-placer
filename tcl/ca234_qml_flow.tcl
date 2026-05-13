# Sky130 CA234 QML-Enhanced Global Placement Flow
# ════════════════════════════════════════════════════════════════════════════
# Replaces standard RePlAce global_placement with QML-optimized placement engine
# Target: Sky130 HD PDK with CA234 design

# Set environment variables
set env(DESIGN_NAME) "CA234"
set env(PDK) "sky130"
set env(PDK_ROOT) $::env(PDK_ROOT)

# Read Sky130 PDK files
puts "\[QML-FLOW\] Reading Sky130 PDK..."

read_lef $::env(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd.tlef
read_lef $::env(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
read_liberty $::env(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib

puts "\[QML-FLOW\] PDK loaded"

# Read CA234 design
puts "\[QML-FLOW\] Reading CA234 design files..."

read_verilog ./designs/CA234/CA234.v
link_design CA234
read_sdc ./designs/CA234/CA234.sdc

puts "\[QML-FLOW\] Design linked"

# Floorplanning with Sky130 site parameters
puts "\[QML-FLOW\] Initializing floorplan with 55% utilization..."

initialize_floorplan \
  -utilization 55 \
  -aspect_ratio 1.0 \
  -core_space 10.0 \
  -site unithd

# Sky130 power straps
puts "\[QML-FLOW\] Setting up power connections..."

add_global_connection -net VDD -pin_pattern {^VPB$} -power
add_global_connection -net VSS -pin_pattern {^VNB$} -ground
global_connect

# Place I/O pins on metal3/metal4
puts "\[QML-FLOW\] Placing I/O pins..."

place_pins -hor_layers met3 -ver_layers met4

# ════════════════════════════════════════════════════════════════════════════
# CRITICAL: Load QML placer hook (replaces standard global_placement)
# ════════════════════════════════════════════════════════════════════════════

puts "\[QML-FLOW\] Loading QML placement hook..."
source ./tcl/qml_placer_hook.tcl

# Standard placement call now routes to QML engine
puts "\[QML-FLOW\] Starting global placement with QML engine..."

global_placement -density 0.55

# ════════════════════════════════════════════════════════════════════════════
# Post-placement standard OpenROAD flow
# ════════════════════════════════════════════════════════════════════════════

puts "\[QML-FLOW\] Running post-placement legalization..."

estimate_parasitics -placement
detailed_placement

puts "\[QML-FLOW\] Checking placement..."

check_placement -verbose

# Power delivery network routing
puts "\[QML-FLOW\] Setting up PDN stripes..."

add_pdn_stripe -layer met1 -width 0.48
route_guides

# Global and detailed routing
puts "\[QML-FLOW\] Routing..."

global_route -guide_file ./results/CA234_route.guide
detailed_route -output_drc ./results/CA234_drc.rpt

# Generate reports
puts "\[QML-FLOW\] Generating reports..."

report_checks -path_delay min_max -format full_clock_expanded > ./results/CA234_timing.rpt
report_wns -digits 4
report_tns -digits 4
report_power > ./results/CA234_power.rpt
report_cell_usage > ./results/CA234_cell_usage.rpt

# Placement DRC check
puts "\[QML-FLOW\] Checking placement DRC..."

check_placement -verbose > ./results/CA234_placement_drc.rpt

# Write results
puts "\[QML-FLOW\] Writing final design files..."

write_def ./results/CA234_placed.def
write_verilog ./results/CA234_placed.v

puts "\[QML-FLOW\] ════════════════════════════════════════════════════════════"
puts "\[QML-FLOW\] CA234 Sky130 QML-Enhanced Flow COMPLETE"
puts "\[QML-FLOW\] Results: ./results/"
puts "\[QML-FLOW\] ════════════════════════════════════════════════════════════"
