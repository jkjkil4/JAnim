// Required:
//  in vec2 v_coord;
//  vec2 get_point(int idx)

#include "../../includes/is_approx_line.glsl"
#include "../../includes/bezier_sdf.glsl"

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
