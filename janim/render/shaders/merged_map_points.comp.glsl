#version 430 core

layout(local_size_x = 256) in;

// Input: raw 3D points for ALL items, packed contiguously
layout(std430, binding = 0) buffer InputPoints {
    vec4 in_points[];       // (x, y, z, 0)
};

// Output: mapped 2D screen-space points for ALL items
layout(std430, binding = 1) buffer OutputPoints {
    vec4 out_points[];      // (x, y, 0, 0)
};

// ItemInfo for looking up which item owns each point
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

layout(std430, binding = 2) buffer ItemInfos {
    ItemInfo item_infos[];
};

uniform int item_count;
uniform mat4 JA_VIEW_MATRIX;
uniform mat4 JA_PROJ_MATRIX;
uniform float JA_FIXED_DIST_FROM_PLANE;
uniform vec2 JA_FRAME_RADIUS;

// Binary search to find which item owns global point index
int find_item(uint global_idx) {
    int lo = 0, hi = item_count - 1;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        if (item_infos[mid].point_offset <= int(global_idx)) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    return lo;
}

void main() {
    uint index = gl_GlobalInvocationID.x;
    if (index >= in_points.length())
        return;

    int item_idx = find_item(index);
    bool fix = item_infos[item_idx].fix_in_frame != 0;

    vec4 point;
    if (fix) {
        point = JA_PROJ_MATRIX * vec4(in_points[index].xy, in_points[index].z - JA_FIXED_DIST_FROM_PLANE, 1.0);
    } else {
        point = JA_PROJ_MATRIX * JA_VIEW_MATRIX * vec4(in_points[index].xyz, 1.0);
    }
    out_points[index].xy = (point.xy / point.w) * JA_FRAME_RADIUS;
    out_points[index].zw = vec2(0.0);
}
