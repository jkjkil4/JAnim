#version 330 core

in vec2 v_coord;

flat in int curr_idx;

out vec4 f_color;

uniform float JA_CAMERA_SCALED_FACTOR;
uniform float JA_ANTI_ALIAS_RADIUS;
uniform bool JA_FIX_IN_FRAME;

uniform vec4 glow_color;
uniform float glow_size;

const float INFINITY = 1.0 / 0.0;

#[JA_FINISH_UP_UNIFORMS]

#include "layouts/layout_compatibility.glsl"

#include "vitem_curve_frag_utils.glsl"
#include "vitem_debug.glsl"

// #define FRAG_AREA

void main()
{
    float d = distance_to_curve(curr_idx);
    f_color = get_vitem_curve_color(d, curr_idx);

    if (f_color.a == 0.0) {
        #ifdef FRAG_AREA
        f_color = vec4(1.0, 0.5, 0.0, 0.5);
        return;
        #endif

        discard;
    }

    #[JA_FINISH_UP]
}
