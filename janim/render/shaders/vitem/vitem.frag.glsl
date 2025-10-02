#version 430 core

in vec2 v_coord;

out vec4 f_color;

uniform float JA_CAMERA_SCALED_FACTOR;
uniform float JA_ANTI_ALIAS_RADIUS;
uniform bool JA_FIX_IN_FRAME;

uniform bool stroke_background;
uniform bool is_fill_transparent;
uniform vec4 glow_color;
uniform float glow_size;

const float INFINITY = uintBitsToFloat(0x7F800000);

#[JA_FINISH_UP_UNIFORMS]

layout(std140, binding = 0) buffer MappedPoints
{
    vec4 points[];  // vec4(x, y, isclosed, 0)
};
layout(std140, binding = 1) buffer Radii
{
    vec4 radii[];   // radii[idx / 4][idx % 4]
};
layout(std140, binding = 2) buffer Colors
{
    vec4 colors[];
};
layout(std140, binding = 3) buffer Fills
{
    vec4 fills[];
};

vec2 get_point(int idx) {
    return points[idx].xy;
}

bool get_isclosed(int idx) {
    return bool(points[idx].z);
}

float get_radius(int anchor_idx) {
    if (JA_FIX_IN_FRAME) {
        return radii[anchor_idx / 4][anchor_idx % 4] * JA_CAMERA_SCALED_FACTOR;
    }
    return radii[anchor_idx / 4][anchor_idx % 4];
}

vec4 get_color(int anchor_idx) {
    return colors[anchor_idx];
}

vec4 get_fill(int anchor_idx) {
    return fills[anchor_idx];
}

#include "../../includes/blend_color.glsl"
#include "vitem_subpath_attr.glsl"
#include "vitem_color.glsl"
#include "vitem_debug.glsl"

// #define CONTROL_POINTS
// #define POLYGON_LINES
// #define SDF_PLANE

void main()
{
    #ifdef CONTROL_POINTS
    if (debug_control_points(points.length()))
        return;
    #endif

    int idx;
    float d = INFINITY;
    float sgn = 1.0;

    int start_idx = 0;
    float sp_d;
    float sp_sgn;

    const int lim = (points.length() - 1) / 2 * 2;

    while (true) {
        get_subpath_attr(start_idx, lim, start_idx, idx, sp_d, sp_sgn);
        d = min(d, sp_d);
        sgn *= sp_sgn;

        if (start_idx >= lim)
            break;
        start_idx += 2;
    }

    f_color = get_vitem_color(d, sgn, idx);

    #if !defined(POLYGON_LINES) && !defined(SDF_PLANE)
    if (f_color.a == 0.0)
        discard;
    #endif

    #ifdef SDF_PLANE
    debug_sdf_plane(sgn, d);
    #endif

    #ifdef POLYGON_LINES
    debug_polygon_lines(points.length());
    #endif

    #[JA_FINISH_UP]
}