// Required:
//  in vec2 v_coord;
//  vec2 get_point(int idx)

#include "../../includes/bezier_sdf.glsl"

float cross2d(vec2 a, vec2 b) {
    return a.x * b.y - a.y * b.x;
}

float distance_to_curve(int idx)
{
    if (idx == -1)
        return INFINITY;

    vec2 A = get_point(idx), B = get_point(idx + 1), C = get_point(idx + 2);
    vec2 v1 = normalize(B - A);
    vec2 v2 = normalize(C - B);
    // REFACTOR: 使用更好的判断可近似为直线的方法
    if (abs(cross2d(v1, v2)) < 1e-3 && dot(v1, v2) > 0.0) {
        vec2 e = C - A;
        vec2 w = v_coord - A;
        vec2 b = w - e * clamp(dot(w, e) / dot(e, e), 0.0, 1.0);
        return length(b);
    } else {
        return distance_bezier(A, B, C, v_coord);
    }
}
