
in vec2 v_coord;

out vec4 f_color;

layout(std140, binding = 0) buffer Points
{
    vec4 points[];  // vec4(x1, y1, x2, y2)
};

uniform float u_anti_alias_radius;
uniform int lim;

vec2 get_point(int idx) {
    int idx_div = idx / 2;
    int idx_mod = idx % 2;
    if (idx_mod == 0) {
        return points[idx_div].xy;
    } else {
        return points[idx_div].zw;
    }
}

#define SKIP_VITEM_GET_SUBPATH_ATTR_INPUTS
#include "../vitem/vitem_plane/subpath_attr.glsl"

void main()
{
    int idx;
    // float stroke_d = INFINITY;  // unused
    float fill_d = INFINITY;
    float fill_sgn = 1.0;

    int start_idx = 0;
    float sp_stroke_d;  // unused
    float sp_fill_d;
    float sp_fill_sgn;

    while (true) {
        get_subpath_attr(start_idx, lim, start_idx, idx, sp_stroke_d, sp_fill_d, sp_fill_sgn);

        // stroke_d = min(stroke_d, sp_stroke_d);
        fill_d = min(fill_d, sp_fill_d);
        fill_sgn *= sp_fill_sgn;

        if (start_idx >= lim)
            break;
        start_idx += 2;
    }

    float fill_sgn_d = fill_d * fill_sgn;
    float a = smoothstep(1, -1, fill_sgn_d / u_anti_alias_radius);

    f_color = vec4(1.0, 1.0, 1.0, a);
}

