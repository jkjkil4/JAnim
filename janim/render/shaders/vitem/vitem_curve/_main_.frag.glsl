
#include "inputs.glsl"
#include "../buffers.glsl"

out vec4 f_color;

#include "frag_utils.glsl"

#define INTEGRATE_GLOW_IN_VITEM_CURVE
#include "../integrate_glow.glsl"

#[JA_FINISH_UP_UNIFORMS]

#include "../debug.glsl"

// #define CONTROL_POINTS
// #define FRAG_AREA

void main()
{
    #if defined(CONTROL_POINTS) && !defined(COMPATIBILITY)
    if (debug_control_points(points.length()))
        return;
    #endif

    float d = distance_to_curve(curr_idx);
    f_color = get_vitem_curve_color(d, curr_idx);

    if (glow_color.a != 0.0) {
        float factor = get_glow_factor(get_lim());

        if (factor > 0.0) {
            vec4 f_glow_color = glow_color;
            f_glow_color.a *= factor;
            f_color = blend_color(f_color, f_glow_color);
        }
    }

    if (f_color.a == 0.0) {
        #ifdef FRAG_AREA
        f_color = vec4(1.0, 0.5, 0.0, 0.5);
        return;
        #endif

        discard;
    }

    #[JA_FINISH_UP]
}

