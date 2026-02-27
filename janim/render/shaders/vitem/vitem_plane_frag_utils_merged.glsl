// Merged version of vitem_plane_frag_utils.glsl
// Uses get_point() which is already redirected through item_infos in the merged frag shader.

#include "../../includes/is_approx_line.glsl"
#include "../../includes/bezier_sdf.glsl"

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
        vec2 e = C - A;
        vec2 w = v_coord - A;
        vec2 b = w - e * clamp(dot(w, e) / dot(e, e), 0.0, 1.0);
        float dist = length(b);
        if (dist < d) {
            d = dist;
            match = true;
        }

        bvec3 cond = bvec3( v_coord.y >= A.y,
                            v_coord.y  < C.y,
                            e.x * w.y > e.y * w.x );
        if(all(cond) || all(not(cond))) sgn = -sgn;
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

uniform vec3 JA_CAMERA_LOC;
uniform vec3 JA_CAMERA_CENTER;
uniform vec3 JA_CAMERA_RIGHT;
uniform vec3 JA_CAMERA_UP;

uniform mat4 JA_VIEW_MATRIX;
uniform mat4 JA_PROJ_MATRIX;

// unit_normal and start_point are #defined as item_infos[v_item_idx].xxx
// DEPTH_TEST is #defined as item_infos[v_item_idx].depth_test != 0

void compute_depth_if_needed()
{
    if (!DEPTH_TEST)
        return;

    vec3 pixel_pos = JA_CAMERA_CENTER + JA_CAMERA_RIGHT * v_coord.x + JA_CAMERA_UP * v_coord.y;

    vec3 ray = pixel_pos - JA_CAMERA_LOC;
    float t = dot(unit_normal, start_point - JA_CAMERA_LOC) / dot(unit_normal, ray);
    vec3 p = JA_CAMERA_LOC + ray * t;

    vec4 clip_space_pos = JA_PROJ_MATRIX * JA_VIEW_MATRIX * vec4(p, 1.0);
    float ndc_depth = clip_space_pos.z / clip_space_pos.w * 0.1;
    gl_FragDepth = (ndc_depth + 1.0) / 2.0;
}
