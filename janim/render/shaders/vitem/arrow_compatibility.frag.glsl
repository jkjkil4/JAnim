#version 330 core

in vec2 v_coord;

out vec4 f_color;

uniform float JA_CAMERA_SCALED_FACTOR;
uniform float JA_ANTI_ALIAS_RADIUS;
uniform bool JA_FIX_IN_FRAME;

uniform bool stroke_background;
uniform bool is_fill_transparent;
uniform vec4 glow_color;
uniform float glow_size;

uniform vec2 shrink; // (left_length, right_length)

const float INFINITY = 1.0 / 0.0;

#[JA_FINISH_UP_UNIFORMS]

uniform int lim;
#include "layouts/layout_compatibility.glsl"

#include "../../includes/blend_color.glsl"
#include "vitem_plane_frag_utils.glsl"
#include "arrow_color.glsl"
#include "vitem_debug.glsl"

// #define CONTROL_POINTS
// #define POLYGON_LINES
// #define SDF_PLANE

void main()
{
    #ifdef CONTROL_POINTS
    if (debug_control_points(lim + 1))
        return;
    #endif

    int idx;
    float stroke_d = INFINITY;
    float fill_d = INFINITY;
    float fill_sgn = 1.0;

    int start_idx = 0;
    float sp_stroke_d;
    float sp_fill_d;
    float sp_fill_sgn;

    while (true) {
        get_subpath_attr(start_idx, lim, start_idx, idx, sp_stroke_d, sp_fill_d, sp_fill_sgn);

        stroke_d = min(stroke_d, sp_stroke_d);
        fill_d = min(fill_d, sp_fill_d);
        fill_sgn *= sp_fill_sgn;

        if (start_idx >= lim)
            break;
        start_idx += 2;
    }

    float shrink_left_length = -1.0;
    float shrink_right_length = -1.0;
    if (idx == 0) {
        shrink_left_length = shrink.x;
    }
    if (idx == lim - 2) {
        shrink_right_length = shrink.y;
    }
    f_color = get_arrow_color(
        stroke_d, fill_d * fill_sgn, idx,
        shrink_left_length, shrink_right_length
    );
    compute_depth_if_needed();

    #if !defined(POLYGON_LINES) && !defined(SDF_PLANE)
    if (f_color.a == 0.0)
        discard;
    #endif

    #ifdef SDF_PLANE
    debug_sdf_plane(fill_sgn, fill_d);
    #endif

    #ifdef POLYGON_LINES
    debug_polygon_lines(lim + 1);
    #endif

    #[JA_FINISH_UP]
}
