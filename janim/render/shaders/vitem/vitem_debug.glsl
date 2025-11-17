// Required:
//  in vec2 v_coord
//  out vec4 f_color
//  vec2 get_point(int idx)

#include "../../includes/blend_color.glsl"

bool debug_control_points(int num)
{
    float d = distance(v_coord, get_point(0));
    for (int i = 1; i < num; i++) {
        d = min(d, distance(v_coord, get_point(i)));
    }
    if (d < 0.06) {
        f_color = vec4(1.0 - smoothstep(0.048, 0.052, d));
        return true;
    }
    return false;
}

void debug_sdf_plane(float sgn, float d)
{
    vec4 sdf_color = vec4(1.0) - sgn * vec4(0.1, 0.4, 0.7, 0.0);
    sdf_color *= 0.8 + 0.2 * cos(140. * d / 3.0);
    sdf_color = mix(sdf_color, vec4(1.0), 1.0 - smoothstep(0.0, 0.02, abs(d)));
    sdf_color.a = 0.5;
    f_color = blend_color(sdf_color, f_color);
}

void debug_polygon_lines(int num)
{
    float d = dot(v_coord - get_point(0), v_coord - get_point(0));
    for(int i = 1, j = 0; i < num; j = i, i++)
    {
        if (get_point(j) == get_point(i)) {
            i++;
            continue;
        }
        // distance
        vec2 e = get_point(j) - get_point(i);
        vec2 w = v_coord - get_point(i);
        vec2 b = w - e * clamp(dot(w, e) / dot(e, e), 0.0, 1.0);
        d = min(d, dot(b, b));
    }
    float line_ratio = smoothstep(1.15, 0.85, sqrt(d) / 0.02);
    f_color.g = max(line_ratio, f_color.g);
    f_color.a = max(line_ratio, f_color.a);
}
