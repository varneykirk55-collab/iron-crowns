// Character-refinement crowd shader, LOD1 (far soldiers): cheap variant of char_vat.gdshaderinc (stage 7 perf).
shader_type spatial;
render_mode cull_disabled;
#define CHAR_NRM1
#define CHAR_NOXF
#define CHAR_VPAL
#include "res://shaders/char_vat.gdshaderinc"
