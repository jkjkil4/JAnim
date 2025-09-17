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

float get_radius(int idx) {
    if (JA_FIX_IN_FRAME) {
        return radii[idx / 4][idx % 4] * JA_CAMERA_SCALED_FACTOR;
    }
    return radii[idx / 4][idx % 4];
}

#include "../includes/blend_color.glsl"
#include "vitem_subpath_attr.glsl"

// #define CONTROL_POINTS
// #define POLYGON_LINES
// #define SDF_PLANE

void main()
{
    float d;

    #ifdef CONTROL_POINTS

    d = distance(v_coord, get_point(0));
    for (int i = 1; i < points.length(); i++) {
        d = min(d, distance(v_coord, get_point(i)));
    }
    if (d < 0.06) {
        f_color = vec4(1.0 - smoothstep(0.048, 0.052, d));
        return;
    }

    #endif

    int idx;
    d = INFINITY;
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
    int anchor_idx = idx / 2;
    float sgn_d = sgn * d;

    vec2 e = get_point(idx + 2) - get_point(idx);
    vec2 w = v_coord - get_point(idx);
    float ratio = clamp(dot(w, e) / dot(e, e), 0.0, 1.0);

    float radius = mix(get_radius(anchor_idx), get_radius(anchor_idx + 1), ratio);

    vec4 fill_color = get_isclosed(idx) ? mix(fills[anchor_idx], fills[anchor_idx + 1], ratio) : vec4(0.0);
    fill_color.a *= smoothstep(1, -1, (sgn_d) / JA_ANTI_ALIAS_RADIUS);

    vec4 stroke_color = mix(colors[anchor_idx], colors[anchor_idx + 1], ratio);
    stroke_color.a *= smoothstep(1, -1, (d - radius) / JA_ANTI_ALIAS_RADIUS);

    if (stroke_background) {
        f_color = blend_color(fill_color, stroke_color);
    } else {
        f_color = blend_color(stroke_color, fill_color);
    }

    if (glow_color.a != 0.0) {
        float factor;
        if (is_fill_transparent) {
            factor = 1.0 - d / glow_size;
        } else {
            factor = 1.0 - sgn_d / glow_size;
        }
        if (0.0 < factor && factor <= 1.0) {
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

    vec4 df_color = vec4(1.0) - sgn * vec4(0.1, 0.4, 0.7, 0.0);
    df_color *= 0.8 + 0.2 * cos(140. * d / 3.0);
    df_color = mix(df_color, vec4(1.0), 1.0 - smoothstep(0.0, 0.02, abs(d)));
    df_color.a = 0.5;
    f_color = blend_color(df_color, f_color);

    #endif

    #ifdef POLYGON_LINES

    const int num = points.length();
    d = dot(v_coord - get_point(0), v_coord - get_point(0));
    for(int i = 1, j = 0; i < num; j = i, i++)
    {
        if (get_point(j) == get_point(i)) {
            i++;
            continue;
        }
        // distance
        vec2 e = get_point(j) - get_point(i);
        vec2 w = v_coord - get_point(i);
        vec2 b = w - e * clamp(dot(w, e) / dot(e, e), 0.0, 1.0);
        d = min(d, dot(b, b));
    }
    float line_ratio = smoothstep(1.15, 0.85, sqrt(d) / 0.02);
    f_color.g = max(line_ratio, f_color.g);
    f_color.a = max(line_ratio, f_color.a);

    #endif

    #[JA_FINISH_UP]
}