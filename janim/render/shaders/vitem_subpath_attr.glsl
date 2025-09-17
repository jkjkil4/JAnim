// Required:
//  vec2 get_point(int idx)
//  bool get_isclosed(int idx)

#include "../includes/bezier_sdf.glsl"

float cross2d(vec2 a, vec2 b) {
    return a.x * b.y - a.y * b.x;
}

void get_subpath_attr(
    int start_idx,
    int lim,
    out int end_idx,
    out int idx,
    out float d,
    out float sgn
) {
    end_idx = lim;
    bool is_closed = get_isclosed(start_idx);

    d = INFINITY;
    sgn = 1.0;
    for (int i = start_idx; i < lim; i += 2) {
        vec2 B = get_point(i + 1);
        if (isnan(B.x)) {
            end_idx = i;
            break;
        }
        vec2 A = get_point(i), C = get_point(i + 2);
        if (A == B && B == C)
            continue;

        vec2 v1 = normalize(B - A);
        vec2 v2 = normalize(C - B);
        // REFACTOR: 使用更好的判断可近似为直线的方法
        if (abs(cross2d(v1, v2)) < 1e-3 && dot(v1, v2) > 0.0) {
            vec2 e = C - A;
            vec2 w = v_coord - A;
            vec2 b = w - e * clamp(dot(w, e) / dot(e, e), 0.0, 1.0);
            float dist = length(b);
            if (dist < d) {
                d = dist;
                idx = i;
            }

            if (is_closed) {
                bvec3 cond = bvec3( v_coord.y >= A.y,
                                    v_coord.y  < C.y,
                                    e.x * w.y > e.y * w.x );
                if(all(cond) || all(not(cond))) sgn = -sgn;
            }
        } else {
            float dist = distance_bezier(A, B, C, v_coord);
            if (dist < d) {
                d = dist;
                idx = i;
            }

            if (is_closed) {
                sgn *= sign_bezier(A, B, C, v_coord);
            }
        }
    }
}