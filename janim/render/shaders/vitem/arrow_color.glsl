// Required:
//  in vec2 v_coord;
//  vec2 get_point(int idx);
//  bool get_isclosed(int idx);
//  float get_radius(int anchor_idx);
//  vec4 get_color(int anchor_idx);
//  vec4 get_fill(int anchor_idx);

vec4 get_arrow_color(
    float d, float sgn, int idx,
    float shrink_left_length, float shrink_right_length
) {
    int anchor_idx = idx / 2;
    float sgn_d = sgn * d;

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
            : smoothstep(left_ratio * 0.95 - 1e-5, left_ratio, orig_ratio),
        shrink_right_length == -1.0
            ? 1.0
            : smoothstep(right_ratio * 0.95 - 1e-5, right_ratio, 1.0 - orig_ratio)
    );
    if (radius <= 0.0)
        radius = -JA_ANTI_ALIAS_RADIUS; // 避免因抗锯齿而被渲染为一个细线

    vec4 fill_color = get_isclosed(idx)
        ? mix(get_fill(anchor_idx), get_fill(anchor_idx + 1), ratio)
        : vec4(0.0);
    fill_color.a *= smoothstep(1, -1, (sgn_d) / JA_ANTI_ALIAS_RADIUS);

    vec4 stroke_color = mix(get_color(anchor_idx), get_color(anchor_idx + 1), ratio);
    stroke_color.a *= smoothstep(1, -1, (d - radius) / JA_ANTI_ALIAS_RADIUS);

    vec4 result_color = stroke_background
        ? blend_color(fill_color, stroke_color)
        : blend_color(stroke_color, fill_color);

    if (glow_color.a != 0.0) {
        float factor;
        if (is_fill_transparent) {
            factor = 1.0 - d / glow_size;
        } else {
            if (sgn_d >= 0.0) {
                factor = 1.0 - sgn_d / glow_size;
            } else {
                factor = 1.0 - (-sgn_d) / JA_ANTI_ALIAS_RADIUS / 2.0;
            }
        }
        if (0.0 < factor && factor <= 1.0) {
            vec4 f_glow_color = glow_color;
            f_glow_color.a *= factor * factor;
            result_color = blend_color(result_color, f_glow_color);
        }
    }

    return result_color;
}
