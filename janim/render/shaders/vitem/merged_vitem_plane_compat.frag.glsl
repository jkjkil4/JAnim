#version 330 core

in vec2 v_coord;
flat in int v_item_idx;

out vec4 f_color;

uniform float JA_CAMERA_SCALED_FACTOR;
uniform float JA_ANTI_ALIAS_RADIUS;

const float INFINITY = 1.0 / 0.0;

#[JA_FINISH_UP_UNIFORMS]

// --- Merged TBO layout (GL 3.3 compatible) ---

// All item data packed into texture buffers
uniform samplerBuffer merged_points;   // vec4(x, y, 0, 0) per point
uniform samplerBuffer merged_radii;    // packed 4 per texel
uniform samplerBuffer merged_colors;   // vec4 RGBA per anchor
uniform samplerBuffer merged_fills;    // vec4 RGBA per anchor

// ItemInfo encoded as 6 vec4 texels per item:
//   texel 0: ivec4(point_offset, point_count, anchor_offset, anchor_count)
//   texel 1: ivec4(fix_in_frame, stroke_background, is_fill_transparent, depth_test)
//   texel 2: vec4(shade_in_3d_as_float, glow_size, 0, 0)
//   texel 3: vec4(glow_color)
//   texel 4: vec4(unit_normal.xyz, 0)
//   texel 5: vec4(start_point.xyz, 0)
uniform samplerBuffer item_info_tbo;

// --- ItemInfo accessors ---

int item_point_offset()  { return floatBitsToInt(texelFetch(item_info_tbo, v_item_idx * 6 + 0).x); }
int item_point_count()   { return floatBitsToInt(texelFetch(item_info_tbo, v_item_idx * 6 + 0).y); }
int item_anchor_offset() { return floatBitsToInt(texelFetch(item_info_tbo, v_item_idx * 6 + 0).z); }
int item_anchor_count()  { return floatBitsToInt(texelFetch(item_info_tbo, v_item_idx * 6 + 0).w); }

bool item_fix_in_frame()        { return floatBitsToInt(texelFetch(item_info_tbo, v_item_idx * 6 + 1).x) != 0; }
bool item_stroke_background()   { return floatBitsToInt(texelFetch(item_info_tbo, v_item_idx * 6 + 1).y) != 0; }
bool item_is_fill_transparent() { return floatBitsToInt(texelFetch(item_info_tbo, v_item_idx * 6 + 1).z) != 0; }
bool item_depth_test()          { return floatBitsToInt(texelFetch(item_info_tbo, v_item_idx * 6 + 1).w) != 0; }

bool  item_shade_in_3d() { return texelFetch(item_info_tbo, v_item_idx * 6 + 2).x != 0.0; }
float item_glow_size()   { return texelFetch(item_info_tbo, v_item_idx * 6 + 2).y; }

vec4 item_glow_color()   { return texelFetch(item_info_tbo, v_item_idx * 6 + 3); }
vec3 item_unit_normal()  { return texelFetch(item_info_tbo, v_item_idx * 6 + 4).xyz; }
vec3 item_start_point()  { return texelFetch(item_info_tbo, v_item_idx * 6 + 5).xyz; }

// --- Per-item data accessors ---

vec2 get_point(int local_idx) {
    return texelFetch(merged_points, item_point_offset() + local_idx).xy;
}

vec3 get_point_with_depth(int local_idx) {
    return texelFetch(merged_points, item_point_offset() + local_idx).xyz;
}

float get_radius(int local_anchor) {
    int global_anchor = item_anchor_offset() + local_anchor;
    float r = texelFetch(merged_radii, global_anchor / 4)[global_anchor % 4];
    if (item_fix_in_frame()) {
        return r * JA_CAMERA_SCALED_FACTOR;
    }
    return r;
}

vec4 get_color(int local_anchor) {
    return texelFetch(merged_colors, item_anchor_offset() + local_anchor);
}

vec4 get_fill(int local_anchor) {
    return texelFetch(merged_fills, item_anchor_offset() + local_anchor);
}

// --- Macros to bridge the shared utility code ---
#define stroke_background item_stroke_background()
#define is_fill_transparent item_is_fill_transparent()
#define glow_color item_glow_color()
#define glow_size item_glow_size()
#define JA_FIX_IN_FRAME item_fix_in_frame()
#define DEPTH_TEST item_depth_test()
#define SHADE_IN_3D item_shade_in_3d()
#define unit_normal item_unit_normal()
#define start_point item_start_point()

#include "../../includes/blend_color.glsl"
#include "vitem_plane_frag_utils_merged.glsl"
#include "vitem_plane_color_merged.glsl"

void main()
{
    int point_count = item_point_count();
    if (point_count < 3)
        discard;

    int idx;
    float stroke_d = INFINITY;
    float fill_d = INFINITY;
    float fill_sgn = 1.0;

    int start_idx = 0;
    float sp_stroke_d;
    float sp_fill_d;
    float sp_fill_sgn;

    const int lim = (point_count - 1) / 2 * 2;

    while (true) {
        get_subpath_attr(start_idx, lim, start_idx, idx, sp_stroke_d, sp_fill_d, sp_fill_sgn);

        stroke_d = min(stroke_d, sp_stroke_d);
        fill_d = min(fill_d, sp_fill_d);
        fill_sgn *= sp_fill_sgn;

        if (start_idx >= lim)
            break;
        start_idx += 2;
    }

    f_color = get_vitem_color(stroke_d, fill_d * fill_sgn, idx);
    compute_depth_if_needed();

    if (f_color.a == 0.0)
        discard;

    #[JA_FINISH_UP]
}
