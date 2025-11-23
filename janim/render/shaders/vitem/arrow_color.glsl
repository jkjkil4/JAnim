// Required:
//  in vec2 v_coord;
//  vec2 get_point(int idx);
//  float get_radius(int anchor_idx);
//  vec4 get_color(int anchor_idx);
//  vec4 get_fill(int anchor_idx);

vec4 get_arrow_color(
    float stroke_d, float fill_sgn_d, int idx,
    float shrink_left_length, float shrink_right_length
) {
    int anchor_idx = idx / 2;

    vec2 e = get_point(idx + 2) - get_point(idx);
    float el = length(e);
    vec2 w = v_coord - get_point(idx);
    float orig_ratio = dot(w, e) / dot(e, e);
    float ratio = clamp(orig_ratio, 0.0, 1.0);

    float radius = mix(get_radius(anchor_idx), get_radius(anchor_idx + 1), ratio);

    float left_ratio = shrink_left_length / el;
    float right_ratio = shrink_right_length / el;
    radius *= min(
        shrink_left_length == -1.0
            ? 1.0
            : smoothstep(left_ratio - 1e-5, left_ratio, orig_ratio),
        shrink_right_length == -1.0
            ? 1.0
            : smoothstep(right_ratio - 1e-5, right_ratio, 1.0 - orig_ratio)
    );
    if (radius <= 0.0)
        radius = -JA_ANTI_ALIAS_RADIUS; // 避免因抗锯齿而被渲染为一个细线

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
