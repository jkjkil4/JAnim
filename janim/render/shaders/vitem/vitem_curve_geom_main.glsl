
vec2 rotate_90_ccw(vec2 v) {
    return vec2(-v.y, v.x);
}

vec2 rotate_90_cw(vec2 v) {
    return vec2(v.y, -v.x);
}

#include "../../includes/is_approx_line.glsl"

void emit_coord(vec2 coord, float depth)
{
    v_coord = coord;
    gl_Position = vec4(v_coord / JA_FRAME_RADIUS, depth * 0.1, 1.0);
    EmitVertex();
}

void main()
{
    int prev_idx = v_prev_idx[0];
    curr_idx = v_curr_idx[0];
    int next_idx = v_next_idx[0];

    vec3 A = get_point_with_depth(curr_idx);
    vec3 B = get_point_with_depth(curr_idx + 1);
    vec3 C = get_point_with_depth(curr_idx + 2);
    if (B == A || B == C) {
        B = (A + C) * 0.5;
    }

    vec2 v1 = normalize(B.xy - A.xy);
    vec2 v2 = normalize(C.xy - B.xy);
    bool flag = cross2d(v1, v2) < 0.0;

    int curr_anchor = curr_idx / 2;
    vec2 r = vec2(get_radius(curr_anchor), get_radius(curr_anchor + 1));
    if (glow_color.a != 0.0) {
        r = max(r, glow_size);
    }
    r += JA_ANTI_ALIAS_RADIUS;

    vec2 expand_start;
    if (prev_idx == -1) {
        expand_start = r.x * (flag ? rotate_90_cw(v1) : rotate_90_ccw(v1));
        A.xy -= r.x * v1;
    } else {
        vec2 before_A = get_point(prev_idx + 1);
        vec2 start_dir;
        if (before_A == A.xy) {
            start_dir = normalize(before_A - get_point(prev_idx));
        } else {
            start_dir = normalize(A.xy - before_A);
        }
        float start_cos = sqrt((dot(start_dir, v1) + 1.0) * 0.5);

        expand_start = normalize(start_dir + v1) * r.x / start_cos;
        expand_start = flag ? rotate_90_cw(expand_start) : rotate_90_ccw(expand_start);
    }

    vec2 expand_end;
    if (next_idx == -1) {
        expand_end = r.y * (flag ? rotate_90_cw(v2) : rotate_90_ccw(v2));
        C.xy += r.y * v2;
    } else {
        vec2 after_C = get_point(next_idx + 1);
        vec2 end_dir;
        if (after_C == C.xy) {
            end_dir = normalize(get_point(next_idx + 2) - after_C);
        } else {
            end_dir = normalize(after_C - C.xy);
        }
        float end_cos = sqrt((dot(end_dir, v2) + 1.0) * 0.5);

        expand_end = normalize(end_dir + v2) * r.y / end_cos;
        expand_end = flag ? rotate_90_cw(expand_end) : rotate_90_ccw(expand_end);
    }

    vec2 p1 = A.xy + expand_start;
    vec2 p2 = A.xy - expand_start;
    vec2 p3 = C.xy + expand_end;
    vec2 p4 = C.xy - expand_end;
    if (is_approx_line(A.xy, B.xy, C.xy)) {
        emit_coord(p1, A.z);
        emit_coord(p2, A.z);
        emit_coord(p3, C.z);
        emit_coord(p4, C.z);
    } else {
        vec2 p_anchor1 = B.xy + r.x * (flag ? rotate_90_ccw(v1) : rotate_90_cw(v1));
        vec2 p_anchor2 = B.xy + r.y * (flag ? rotate_90_ccw(v2) : rotate_90_cw(v2));
        emit_coord(p1, A.z);
        emit_coord(p2, A.z);
        emit_coord(p3, C.z);
        emit_coord(p_anchor1, B.z);
        emit_coord(p4, C.z);
        emit_coord(p_anchor2, B.z);
    }
    EndPrimitive();
}
