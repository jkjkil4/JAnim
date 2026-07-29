#include "../../../includes/shade.glsl"
#include "../../../includes/blend_color.glsl"

#include "inputs.glsl"
#include "../buffers.glsl"

vec4 get_vitem_color(float stroke_d, float fill_sgn_d, int idx, int lim)
{
    int anchor_idx = idx / 2;

    vec2 e = get_point(idx + 2) - get_point(idx);
    vec2 w = v_coord - get_point(idx);
    float ratio = clamp(dot(w, e) / dot(e, e), 0.0, 1.0);

    float radius = mix(get_radius(anchor_idx), get_radius(anchor_idx + 1), ratio);

    #ifdef ARROW
    float orig_ratio = dot(w, e) / dot(e, e);

    float shrink_left_ratio = -1.0;
    float shrink_right_ratio = -1.0;
    if (idx == 0) {
        shrink_left_ratio = shrink.x;
    }
    if (idx == lim - 2) {
        shrink_right_ratio = shrink.y;
    }

    radius *= min(
        shrink_left_ratio == -1.0
            ? 1.0
            : smoothstep(shrink_left_ratio - 1e-5, shrink_left_ratio, orig_ratio),
        shrink_right_ratio == -1.0
            ? 1.0
            : smoothstep(shrink_right_ratio - 1e-5, shrink_right_ratio, 1.0 - orig_ratio)
    );
    #endif

    vec4 fill_color;
    if (is_fill_transparent) {
        fill_color = vec4(0.0);
    } else {
        fill_color = mix(get_fill(anchor_idx), get_fill(anchor_idx + 1), ratio);
        fill_color.a *= smoothstep(1, -1, fill_sgn_d / JA_ANTI_ALIAS_RADIUS);
    }

    vec4 stroke_color = mix(get_color(anchor_idx), get_color(anchor_idx + 1), ratio);
    stroke_color.a *= smoothstep(1, -1, (stroke_d - radius) / JA_ANTI_ALIAS_RADIUS);

    vec4 result_color = stroke_background
        ? blend_color(fill_color, stroke_color)
        : blend_color(stroke_color, fill_color);

    if (SHADE_IN_3D) {
        result_color.rgb = apply_light(result_color.rgb, start_point, unit_normal);
    }

    if (glow_color.a != 0.0) {
        float glow_sgn_d = is_fill_transparent ? stroke_d : min(stroke_d, fill_sgn_d);
        float factor;
        if (glow_sgn_d >= 0.0) {
            factor = 1.0 - glow_sgn_d / glow_size;
        } else {
            factor = 1.0 - (-glow_sgn_d) / JA_ANTI_ALIAS_RADIUS / 2.0;
        }
        if (0.0 < factor && factor <= 1.0) {
            vec4 f_glow_color = glow_color;
            f_glow_color.a *= factor * factor;
            result_color = blend_color(result_color, f_glow_color);
        }
    }

    return result_color;
}
