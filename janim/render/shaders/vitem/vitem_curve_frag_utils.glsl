// Required:
//  in vec2 v_coord;
//  vec2 get_point(int idx);
//  float get_radius(int anchor_idx)
//  vec4 get_color(int anchor_idx)
//  vec4 get_fill(int anchor_idx)

#include "../../includes/is_approx_line.glsl"
#include "../../includes/bezier_sdf.glsl"
#include "../../includes/blend_color.glsl"

float distance_to_curve(int idx)
{
    if (idx == -1)
        return INFINITY;

    vec2 A = get_point(idx), B = get_point(idx + 1), C = get_point(idx + 2);
    if (is_approx_line(A, B, C)) {
        vec2 e = C - A;
        vec2 w = v_coord - A;
        vec2 b = w - e * clamp(dot(w, e) / dot(e, e), 0.0, 1.0);
        return length(b);
    } else {
        return distance_bezier(A, B, C, v_coord);
    }
}

vec4 get_vitem_curve_color(float d, int idx)
{
    int anchor_idx = idx / 2;

    vec2 e = get_point(idx + 2) - get_point(idx);
    vec2 w = v_coord - get_point(idx);
    float ratio = clamp(dot(w, e) / dot(e, e), 0.0, 1.0);

    float radius = mix(get_radius(anchor_idx), get_radius(anchor_idx + 1), ratio);

    vec4 stroke_color = mix(get_color(anchor_idx), get_color(anchor_idx + 1), ratio);
    stroke_color.a *= smoothstep(1, -1, (d - radius) / JA_ANTI_ALIAS_RADIUS);

    vec4 result_color = stroke_color;

    if (glow_color.a != 0.0) {
        float factor = 1.0 - d / glow_size;
        if (0.0 < factor && factor <= 1.0) {
            vec4 f_glow_color = glow_color;
            f_glow_color.a *= factor * factor;
            result_color = blend_color(result_color, f_glow_color);
        }
    }

    return result_color;
}
