## Gamepad map cursor (a reticle, not an on-screen controller): drawn at its own position, moved by main.gd.
class_name PadCursor
extends Control

func _draw() -> void:
	var c := Color(1.0, 0.9, 0.5, 0.95)
	draw_arc(Vector2.ZERO, 14.0, 0.0, TAU, 32, Color(0, 0, 0, 0.6), 5.0)
	draw_arc(Vector2.ZERO, 14.0, 0.0, TAU, 32, c, 2.5)
	for d in [Vector2(1, 0), Vector2(-1, 0), Vector2(0, 1), Vector2(0, -1)]:
		draw_line(d * 6.0, d * 20.0, c, 2.0)
	draw_circle(Vector2.ZERO, 2.0, c)
