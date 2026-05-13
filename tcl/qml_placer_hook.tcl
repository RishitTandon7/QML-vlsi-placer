# QML Placement Engine Hook for OpenROAD TCL
# ════════════════════════════════════════════════════════════════════════════
# Intercepts global_placement command and routes to Python QML placement engine
# Provides seamless integration with existing OpenROAD TCL flows

# Rename original global_placement for fallback
rename global_placement __orig_global_placement

# Define QML-enhanced placement procedure
proc global_placement {args} {
    # Parse arguments
    set density 0.55
    set config_file "configs/ca234_sky130.json"
    
    # Extract density argument if provided
    set density_idx [lsearch $args -density]
    if {$density_idx >= 0 && [expr {$density_idx + 1}] < [llength $args]} {
        set density [lindex $args [expr {$density_idx + 1}]]
    }
    
    puts "\[QML-PLACER\] ════════════════════════════════════════════════════════════"
    puts "\[QML-PLACER\] QML-Enhanced Global Placement Engine"
    puts "\[QML-PLACER\] Target Density: $density"
    puts "\[QML-PLACER\] ════════════════════════════════════════════════════════════"
    
    # Call Python QML placement engine via subprocess
    set rc [catch {
        exec python3 ./core/qml_placer_bridge.py \
            --density $density \
            --config $config_file \
            2>@stderr
    } output]
    
    if {$rc != 0} {
        puts "\[QML-PLACER\] ERROR: QML placement failed"
        puts "\[QML-PLACER\] Output: $output"
        puts "\[QML-PLACER\] Falling back to standard RePlAce placer..."
        
        # Fallback to original placer on error
        __orig_global_placement {*}$args
        
        return -code error "QML placement failed, fallback used"
    } else {
        puts "\[QML-PLACER\] QML Placement Complete"
        puts "\[QML-PLACER\] Output:"
        puts $output
        puts "\[QML-PLACER\] ════════════════════════════════════════════════════════════"
    }
}

# Procedure to revert to standard placer (for comparison mode)
proc use_standard_placer {} {
    puts "\[QML-PLACER\] Reverting to standard RePlAce placer"
    rename global_placement __qml_global_placement
    rename __orig_global_placement global_placement
}

# Procedure to switch back to QML placer
proc use_qml_placer {} {
    puts "\[QML-PLACER\] Switching back to QML placer"
    rename global_placement __orig_global_placement
    rename __qml_global_placement global_placement
}

puts "\[QML-PLACER\] QML placement hook loaded successfully"
