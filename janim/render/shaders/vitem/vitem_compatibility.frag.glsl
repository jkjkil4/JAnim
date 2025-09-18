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

const float INFINITY = 1.0 / 0.0;

#[JA_FINISH_UP_UNIFORMS]

uniform int lim;
uniform samplerBuffer points;   // vec4(x, y, isclosed, 0)
uniform samplerBuffer radii;    // radii[idx / 4][idx % 4]
uniform samplerBuffer colors;
uniform samplerBuffer fills;

vec2 get_point(int idx) {
    return texelFetch(points, idx).xy;
}

bool get_isclosed(int idx) {
    return bool(texelFetch(points, idx).z);
}

float get_radius(int idx) {
    if (JA_FIX_IN_FRAME) {
        return texelFetch(radii, idx / 4)[idx % 4] * JA_CAMERA_SCALED_FACTOR;
    }
    return texelFetch(radii, idx / 4)[idx % 4];
}

#include "../../includes/blend_color.glsl"
#include "vitem_subpath_attr.glsl"
#include "vitem_debug.glsl"

// #define CONTROL_POINTS
// #define POLYGON_LINES
// #define SDF_PLANE

void main()
{
    #ifdef CONTROL_POINTS
    if (debug_control_points(lim * 2 + 1))
        return;
    #endif

    int idx;
    float d = INFINITY;
    float sgn = 1.0;

    int start_idx = 0;
    float sp_d;
    float sp_sgn;

    while (true) {
        get_subpath_attr(start_idx, lim, start_idx, idx, sp_d, sp_sgn);
        d = min(d, sp_d);
        sgn *= sp_sgn;

        if (start_idx >= lim)
            break;
        start_idx += 2;
    }
    int anchor_idx = idx / 2;
    float sgn_d = sgn * d;

    vec2 e = get_point(idx + 2) - get_point(idx);
    vec2 w = v_coord - get_point(idx);
    float ratio = clamp(dot(w, e) / dot(e, e), 0.0, 1.0);

    float radius = mix(get_radius(anchor_idx), get_radius(anchor_idx + 1), ratio);

    vec4 fill_color = get_isclosed(idx)
        ? mix(texelFetch(fills, anchor_idx), texelFetch(fills, anchor_idx + 1), ratio)
        : vec4(0.0);
    fill_color.a *= smoothstep(1, -1, (sgn_d) / JA_ANTI_ALIAS_RADIUS);

    vec4 stroke_color = mix(texelFetch(colors, anchor_idx), texelFetch(colors, anchor_idx + 1), ratio);
    stroke_color.a *= smoothstep(1, -1, (d - radius) / JA_ANTI_ALIAS_RADIUS);

    if (stroke_background) {
        f_color = blend_color(fill_color, stroke_color);
    } else {
        f_color = blend_color(stroke_color, fill_color);
    }

    if (glow_color.a != 0.0) {
        float factor;
        if (is_fill_transparent) {
            factor = 1 - d / glow_size;
        } else {
            if (sgn_d >= 0) {
                factor = 1 - sgn_d / glow_size;
            } else {
                factor = 1 - (-sgn_d) / JA_ANTI_ALIAS_RADIUS / 2;
            }
        }
        if (0 < factor && factor <= 1) {
            vec4 f_glow_color = glow_color;
            f_glow_color.a *= factor * factor;
            f_color = blend_color(f_color, f_glow_color);
        }
    }

    #if !defined(POLYGON_LINES) && !defined(SDF_PLANE)
    if (f_color.a == 0.0)
        discard;
    #endif

    #ifdef SDF_PLANE
    debug_sdf_plane(sgn, d);
    #endif

    #ifdef POLYGON_LINES
    debug_polygon_lines(lim * 2 + 1);
    #endif

    #[JA_FINISH_UP]
}
