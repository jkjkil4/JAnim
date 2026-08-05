#include "../../../includes/infinity.glsl"

#include "../is_approx_line.glsl"
#include "../line_sdf.glsl"
#include "../bezier_sdf.glsl"

#include "inputs.glsl"
#include "../buffers.glsl"

void get_curve_attr(
    vec2 A,
    vec2 B,
    vec2 C,
    inout bool match,
    inout float d,
    inout float sgn
) {
    if (A == B && B == C)
        return;

    if (is_approx_line(A, B, C)) {
        float dist = distance_line(A, C, v_coord);
        if (dist < d) {
            d = dist;
            match = true;
        }

        sgn *= sign_line(A, C, v_coord);
    } else {
        float dist = distance_bezier(A, B, C, v_coord);
        if (dist < d) {
            d = dist;
            match = true;
        }

        sgn *= sign_bezier(A, B, C, v_coord);
    }
}

void get_subpath_attr(
    int start_idx,
    int lim,
    out int end_idx,
    out int idx,
    out float stroke_d,
    out float fill_d,
    out float fill_sgn
) {
    end_idx = lim;

    stroke_d = INFINITY;
    fill_sgn = 1.0;

    bool match;

    for (int i = start_idx; i < lim; i += 2) {
        vec2 B = get_point(i + 1);
        if (isnan(B.x)) {
            end_idx = i;
            break;
        }
        vec2 A = get_point(i), C = get_point(i + 2);

        match = false;
        get_curve_attr(A, B, C, match, stroke_d, fill_sgn);
        if (match) {
            idx = i;
        }
    }

    vec2 A = get_point(end_idx);
    vec2 C = get_point(start_idx);
    vec2 B = (A + C) * 0.5;
    fill_d = stroke_d;
    get_curve_attr(A, B, C, match, fill_d, fill_sgn);
}
