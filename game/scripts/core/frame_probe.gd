## Measures wall-clock CPU time of the whole _process pass: one probe runs first (priority -10000) and one
## runs last (+10000); script_ms = end - start. Rendering happens after the process pass, so on a display
## build frame_ms - script_ms approximates render + engine overhead.
class_name FrameProbe
extends Node

static var t_start := 0
static var script_us := 0
var is_end := false

func _init(end_probe: bool = false) -> void:
	is_end = end_probe
	process_priority = 10000 if end_probe else -10000
	process_mode = Node.PROCESS_MODE_ALWAYS

func _process(_d: float) -> void:
	if is_end:
		script_us = Time.get_ticks_usec() - t_start
	else:
		t_start = Time.get_ticks_usec()
