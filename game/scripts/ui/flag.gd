## Simple procedural flag (original, simplified patterns from nations.json).
class_name FlagRect
extends Control

var pattern: Array = []
var fallback := Color(0.5, 0.5, 0.5)

func set_nation(code: String) -> void:
	pattern = []
	if Sim.nations.has(code):
		pattern = Sim.nations[code].get("flag", [])
		fallback = Sim.nations[code]["color"]
	queue_redraw()

## Works before a game exists (main menu): reads the static nation data.
func set_nation_static(code: String) -> void:
	pattern = []
	if GameData.majors.has(code):
		pattern = GameData.majors[code].get("flag", [])
		fallback = Color(GameData.majors[code].get("color", "#808080"))
	queue_redraw()

func _draw() -> void:
	var r := Rect2(Vector2.ZERO, size)
	if pattern.is_empty():
		draw_rect(r, fallback)
		draw_rect(Rect2(0, size.y * 0.4, size.x, size.y * 0.2), fallback.darkened(0.4))
	else:
		var kind: String = pattern[0]
		var cols: Array = []
		for i in range(1, pattern.size()):
			cols.append(Color(pattern[i]))
		match kind:
			"fess":
				for i in cols.size():
					draw_rect(Rect2(0, size.y * i / cols.size(), size.x, size.y / cols.size() + 0.5), cols[i])
			"pale":
				for i in cols.size():
					draw_rect(Rect2(size.x * i / cols.size(), 0, size.x / cols.size() + 0.5, size.y), cols[i])
			"disc":
				draw_rect(r, cols[0])
				draw_circle(size * 0.5, size.y * 0.3, cols[1] if cols.size() > 1 else Color.RED)
			"cross":
				draw_rect(r, cols[0])
				var c: Color = cols[1] if cols.size() > 1 else Color.WHITE
				draw_rect(Rect2(size.x * 0.3, 0, size.x * 0.14, size.y), c)
				draw_rect(Rect2(0, size.y * 0.42, size.x, size.y * 0.16), c)
				if cols.size() > 2:   # Nordic cross with an inner cross (e.g. Norway, Iceland)
					draw_rect(Rect2(size.x * 0.33, 0, size.x * 0.08, size.y), cols[2])
					draw_rect(Rect2(0, size.y * 0.45, size.x, size.y * 0.10), cols[2])
			"canton":
				for i in 7:
					draw_rect(Rect2(0, size.y * i / 7.0, size.x, size.y / 7.0 + 0.5), cols[0] if i % 2 == 0 else cols[1])
				draw_rect(Rect2(0, 0, size.x * 0.42, size.y * 4.0 / 7.0), cols[2] if cols.size() > 2 else Color.NAVY_BLUE)
			_:
				draw_rect(r, cols[0] if cols.size() > 0 else fallback)
	draw_rect(r, Color(0, 0, 0, 0.8), false, 1.0)
