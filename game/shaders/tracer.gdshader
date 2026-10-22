shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled;
varying vec4 tcol;
void vertex() { tcol = INSTANCE_CUSTOM; }
void fragment() { ALBEDO = tcol.rgb; }
