in vec2 v_coord;

uniform bool stroke_background;
uniform bool is_fill_transparent;
uniform vec4 glow_color;
uniform float glow_size;

uniform vec3 unit_normal;
uniform vec3 start_point;
uniform bool DEPTH_TEST;
uniform bool SHADE_IN_3D;

#ifdef ARROW
uniform vec2 shrink;
#endif

