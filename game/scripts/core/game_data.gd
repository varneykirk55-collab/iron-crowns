extends Node
## Static game data: map rasters, provinces, countries, sea zones, nations, eras and units.
## Everything is data-driven from res://data/*.json so new nations/units/eras can be added without code.

const MAP_W := 360.0          # world units across (1 unit = 1 degree of longitude)
const MAP_H := 180.0
const HEIGHT_SCALE := 0.42    # world units per km of elevation (exaggerated for readability)
const SEA_NODE := 100000      # graph node offset for sea zones
const WASTELAND := 65535

var provinces := {}           # id -> Dictionary (static data)
var province_ids: Array = []  # sorted list of land province ids
var countries := {}           # code -> Dictionary
var seazones := {}            # id -> Dictionary
var majors := {}              # code -> nation definition
var playable: Array = []
var eras: Array = []
var start_years: Array = []
var units := {}               # id -> unit definition
var units_by_era := {}        # era id -> Array of unit ids
var era_tier := {}
var resources: Array = []
var resource_price := 2.0

var raster_w := 0
var raster_h := 0
var prov_bytes: PackedByteArray
var prov_image: Image
var height_image: Image
var sea_w := 0
var sea_h := 0
var sea_bytes: PackedByteArray
var albedo_texture: Texture2D
var loaded := false

func _ready() -> void:
	load_all()

func _json(path: String) -> Variant:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("missing " + path)
		return null
	return JSON.parse_string(f.get_as_text())

func load_all() -> void:
	if loaded:
		return
	var t0 := Time.get_ticks_msec()
	var pj: Dictionary = _json("res://data/map/provinces.json")
	raster_w = int(pj["width"]); raster_h = int(pj["height"])
	for p in pj["provinces"]:
		var nb := {}
		for k in p["neighbors"].keys():
			nb[int(k)] = int(p["neighbors"][k])
		p["neighbors"] = nb
		var sz: Array = []
		for s in p["seazones"]:
			sz.append(int(s))
		p["seazones"] = sz
		p["id"] = int(p["id"])
		provinces[p["id"]] = p
	province_ids = provinces.keys()
	province_ids.sort()
	for c in _json("res://data/map/countries.json"):
		var pl: Array = []
		for i in c["provinces"]:
			pl.append(int(i))
		c["provinces"] = pl
		c["capital"] = int(c["capital"])
		countries[c["code"]] = c
	var sj: Dictionary = _json("res://data/map/seazones.json")
	sea_w = int(sj["width"]); sea_h = int(sj["height"])
	for z in sj["zones"]:
		z["id"] = int(z["id"])
		var nb2: Array = []
		for n in z["neighbors"]:
			nb2.append(int(n))
		z["neighbors"] = nb2
		z["ports"] = []
		seazones[z["id"]] = z
	for pid in province_ids:
		for zid in provinces[pid]["seazones"]:
			if seazones.has(zid):
				seazones[zid]["ports"].append(pid)
	var nj: Dictionary = _json("res://data/nations.json")
	playable = nj["playable"]
	for n in nj["majors"]:
		majors[n["code"]] = n
	var ej: Dictionary = _json("res://data/eras.json")
	eras = ej["eras"]
	start_years = ej["start_years"]
	var uj: Dictionary = _json("res://data/units.json")
	era_tier = uj["era_tier"]
	resources = uj["resources"]
	resource_price = float(uj["resource_price"])
	for u in uj["units"]:
		units[u["id"]] = u
		if not units_by_era.has(u["era"]):
			units_by_era[u["era"]] = []
		units_by_era[u["era"]].append(u["id"])
	# rasters (raw binary so ids are never touched by texture compression)
	prov_bytes = FileAccess.get_file_as_bytes("res://data/map/province_ids.bin")
	prov_image = Image.create_from_data(raster_w, raster_h, false, Image.FORMAT_RG8, prov_bytes)
	var hb := FileAccess.get_file_as_bytes("res://data/map/heights.bin")
	height_image = Image.create_from_data(raster_w / 2, raster_h / 2, false, Image.FORMAT_RH, hb)
	sea_bytes = FileAccess.get_file_as_bytes("res://data/map/seazone_ids.bin")
	var img := Image.new()
	var ab := FileAccess.get_file_as_bytes("res://data/map/albedo.jpg")
	img.load_jpg_from_buffer(ab)
	img.generate_mipmaps()
	albedo_texture = ImageTexture.create_from_image(img)
	loaded = true
	print("[GameData] loaded %d provinces, %d countries, %d sea zones in %d ms" % [provinces.size(), countries.size(), seazones.size(), Time.get_ticks_msec() - t0])

# ---------- geography helpers ----------
func lonlat_to_world(lon: float, lat: float) -> Vector2:
	return Vector2(lon + 180.0, 90.0 - lat)

func world_to_lonlat(x: float, z: float) -> Vector2:
	return Vector2(x - 180.0, 90.0 - z)

func province_at_world(x: float, z: float) -> int:
	var px := int(floor(x / MAP_W * raster_w))
	var py := int(floor(z / MAP_H * raster_h))
	if py < 0 or py >= raster_h:
		return 0
	px = posmod(px, raster_w)
	var i := (py * raster_w + px) * 2
	return prov_bytes[i] | (prov_bytes[i + 1] << 8)

func seazone_at_world(x: float, z: float) -> int:
	var px := posmod(int(floor(x / MAP_W * sea_w)), sea_w)
	var py := clampi(int(floor(z / MAP_H * sea_h)), 0, sea_h - 1)
	var i := (py * sea_w + px) * 2
	return sea_bytes[i] | (sea_bytes[i + 1] << 8)

func height_km_at_world(x: float, z: float) -> float:
	var w := height_image.get_width(); var h := height_image.get_height()
	var px := posmod(int(x / MAP_W * w), w)
	var py := clampi(int(z / MAP_H * h), 0, h - 1)
	return maxf(height_image.get_pixel(px, py).r, 0.0)

func surface_y(x: float, z: float) -> float:
	if province_at_world(x, z) == 0:
		return 0.0
	return maxf(height_km_at_world(x, z), 0.03) * HEIGHT_SCALE

func node_lonlat(node: int) -> Vector2:
	if node >= SEA_NODE:
		var z: Dictionary = seazones[node - SEA_NODE]
		return Vector2(z["lon"], z["lat"])
	var p: Dictionary = provinces[node]
	return Vector2(p["lon"], p["lat"])

func node_world(node: int) -> Vector3:
	var ll := node_lonlat(node)
	var w := lonlat_to_world(ll.x, ll.y)
	return Vector3(w.x, surface_y(w.x, w.y), w.y)

func km_between(a: Vector2, b: Vector2) -> float:
	var la1 := deg_to_rad(a.y); var la2 := deg_to_rad(b.y)
	var dl := deg_to_rad(b.x - a.x); var dp := la2 - la1
	var h := sin(dp / 2) ** 2 + cos(la1) * cos(la2) * sin(dl / 2) ** 2
	return 6371.0 * 2.0 * asin(sqrt(minf(h, 1.0)))

func node_km(a: int, b: int) -> float:
	return maxf(km_between(node_lonlat(a), node_lonlat(b)), 40.0)

func era_index(era_id: String) -> int:
	for i in eras.size():
		if eras[i]["id"] == era_id:
			return i
	return 0

func era_for_year(year: float) -> int:
	var idx := 0
	for i in eras.size():
		if year >= float(eras[i]["start"]):
			idx = i
	return idx

func unit_for_role(era_id: String, role: String) -> String:
	for uid in units_by_era.get(era_id, []):
		if units[uid]["role"] == role:
			return uid
	# fall back to the closest role
	var fallback := {"inf": "ranged", "ranged": "inf", "cav": "armor", "armor": "cav", "art": "art"}
	for uid in units_by_era.get(era_id, []):
		if units[uid]["role"] == fallback.get(role, "inf"):
			return uid
	return units_by_era[era_id][0]

func nation_color(code: String) -> Color:
	if majors.has(code):
		return Color(majors[code]["color"])
	# deterministic muted colour for minor polities
	var h := float(hash(code) % 1000) / 1000.0
	return Color.from_hsv(h, 0.28 + float(hash(code + "s") % 100) / 600.0, 0.62 + float(hash(code + "v") % 100) / 700.0)

func country_name(code: String) -> String:
	return countries[code]["name"] if countries.has(code) else code
