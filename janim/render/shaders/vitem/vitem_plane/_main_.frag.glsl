#include "inputs.glsl"
#include "../buffers.glsl"

#ifdef COMPATIBILITY
uniform int lim;
int get_lim() { return lim; }
#else
int get_lim() { return (points.length() - 1) / 2 * 2; }
#endif

out vec4 f_color;

#include "subpath_attr.glsl"
#include "compute_depth.glsl"
#include "get_color.glsl"

#include "../../../includes/infinity.glsl"

#[JA_FINISH_UP_UNIFORMS]

#include "../debug.glsl"
// #define CONTROL_POINTS
// #define POLYGON_LINES
// #define SDF_PLANE

void main()
{
    int lim = get_lim();

    #ifdef CONTROL_POINTS
    if (debug_control_points(v_coord, lim + 1))
        return
    #endif

    int idx;
    float stroke_d = INFINITY;
    float fill_d = INFINITY;
    float fill_sgn = 1.0;

    int start_idx = 0;
    float sp_stroke_d;
    float sp_fill_d;
    float sp_fill_sgn;

    while (true) {
        get_subpath_attr(start_idx, lim, start_idx, idx, sp_stroke_d, sp_fill_d, sp_fill_sgn);

        stroke_d = min(stroke_d, sp_stroke_d);
        fill_d = min(fill_d, sp_fill_d);
        fill_sgn *= sp_fill_sgn;

        if (start_idx >= lim)
            break;
        start_idx += 2;
    }

    f_color = get_vitem_color(stroke_d, fill_d * fill_sgn, idx, lim);
    compute_depth_if_needed();

    #if !defined(POLYGON_LINES) && !defined(SDF_PLANE)
    if (f_color.a == 0.0)
        discard;
    #endif

    #ifdef SDF_PLANE
    debug_sdf_plane(fill_sgn, fill_d);
    #endif

    #ifdef POLYGON_LINES
    debug_polygon_lines(v_coord, lim + 1);
    #endif

    #[JA_FINISH_UP]
}

