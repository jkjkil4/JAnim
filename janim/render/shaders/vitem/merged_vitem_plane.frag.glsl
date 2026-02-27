#version 430 core

in vec2 v_coord;
flat in int v_item_idx;

out vec4 f_color;

uniform float JA_CAMERA_SCALED_FACTOR;
uniform float JA_ANTI_ALIAS_RADIUS;

const float INFINITY = uintBitsToFloat(0x7F800000);

#[JA_FINISH_UP_UNIFORMS]

// --- Merged SSBO layout ---

struct ItemInfo {
    int point_offset;
    int point_count;
    int anchor_offset;
    int anchor_count;
    int fix_in_frame;
    int stroke_background;
    int is_fill_transparent;
    int depth_test;
    int shade_in_3d;
    float glow_size;
    float _pad0;
    float _pad1;
    vec4 glow_color;
    vec3 unit_normal;
    float _pad2;
    vec3 start_point;
    float _pad3;
};

layout(std430, binding = 0) buffer MergedMappedPoints {
    vec4 points_data[];
};

layout(std430, binding = 1) buffer MergedRadii {
    vec4 radii_data[];
};

layout(std430, binding = 2) buffer MergedColors {
    vec4 colors_data[];
};

layout(std430, binding = 3) buffer MergedFills {
    vec4 fills_data[];
};

layout(std430, binding = 4) buffer ItemInfos {
    ItemInfo item_infos[];
};

// --- Per-item accessors using v_item_idx ---

// These replace the original layout.glsl accessors, redirecting through item_infos

vec2 get_point(int local_idx) {
    return points_data[item_infos[v_item_idx].point_offset + local_idx].xy;
}

vec3 get_point_with_depth(int local_idx) {
    return points_data[item_infos[v_item_idx].point_offset + local_idx].xyz;
}

float get_radius(int local_anchor) {
    int global_anchor = item_infos[v_item_idx].anchor_offset + local_anchor;
    if (item_infos[v_item_idx].fix_in_frame != 0) {
        return radii_data[global_anchor / 4][global_anchor % 4] * JA_CAMERA_SCALED_FACTOR;
    }
    return radii_data[global_anchor / 4][global_anchor % 4];
}

vec4 get_color(int local_anchor) {
    return colors_data[item_infos[v_item_idx].anchor_offset + local_anchor];
}

vec4 get_fill(int local_anchor) {
    return fills_data[item_infos[v_item_idx].anchor_offset + local_anchor];
}

// --- Per-item uniform substitutes (read from ItemInfo) ---

// These replace the per-item uniforms that were set individually before
#define stroke_background (item_infos[v_item_idx].stroke_background != 0)
#define is_fill_transparent (item_infos[v_item_idx].is_fill_transparent != 0)
#define glow_color (item_infos[v_item_idx].glow_color)
#define glow_size (item_infos[v_item_idx].glow_size)
#define JA_FIX_IN_FRAME (item_infos[v_item_idx].fix_in_frame != 0)
#define DEPTH_TEST (item_infos[v_item_idx].depth_test != 0)
#define SHADE_IN_3D (item_infos[v_item_idx].shade_in_3d != 0)
#define unit_normal (item_infos[v_item_idx].unit_normal)
#define start_point (item_infos[v_item_idx].start_point)

#include "../../includes/blend_color.glsl"
#include "vitem_plane_frag_utils_merged.glsl"
#include "vitem_plane_color_merged.glsl"

void main()
{
    int point_count = item_infos[v_item_idx].point_count;
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
