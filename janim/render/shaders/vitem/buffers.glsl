// 在 Compatibility Mode 下，使用 Texture Buffer 传递 array data
// 在 Normal Mode 下，使用 SSBO 传递 array data
// 
// 均提供了如下函数：
// 
// vec2 get_point(int idx)
// vec3 get_point_with_depth(int idx)
// float get_radius(int anchor_idx)
// vec4 get_color(int anchor_idx)
// vec4 get_fill(int anchor_idx)
//
// 其中与 fill 相关的在 vitem-curve 中未使用，会被 GLSL 静默移除

#include "../../includes/janim_globals.glsl"

#ifdef COMPATIBILITY

uniform samplerBuffer points;   // vec4(x, y, 0 or depth, 0)
                                // 在 vitem_plane 中 z 分量为 0，在 vitem_curve 中表示 depth

uniform samplerBuffer radii;    // radii[idx / 4][idx % 4]
uniform samplerBuffer colors;
uniform samplerBuffer fills;

vec2 get_point(int idx) {
    return texelFetch(points, idx).xy;
}

vec3 get_point_with_depth(int idx) {
    return texelFetch(points, idx).xyz;
}

float get_radius(int anchor_idx) {
    if (JA_FIX_IN_FRAME) {
        return texelFetch(radii, anchor_idx / 4)[anchor_idx % 4] * JA_CAMERA_SCALED_FACTOR;
    }
    return texelFetch(radii, anchor_idx / 4)[anchor_idx % 4];
}

vec4 get_color(int anchor_idx) {
    return texelFetch(colors, anchor_idx);
}

vec4 get_fill(int anchor_idx) {
    return texelFetch(fills, anchor_idx);
}

#else

layout(std140, binding = 0) buffer MappedPoints
{
    vec4 points[];  // vec4(x, y, 0 or depth, 0)
                    // 在 vitem_plane 中 z 分量为 0，在 vitem_curve 中表示 depth
};
layout(std140, binding = 1) buffer Radii
{
    vec4 radii[];   // radii[idx / 4][idx % 4]
};
layout(std140, binding = 2) buffer Colors
{
    vec4 colors[];
};
layout(std140, binding = 3) buffer Fills
{
    vec4 fills[];
};

vec2 get_point(int idx) {
    return points[idx].xy;
}

vec3 get_point_with_depth(int idx) {
    return points[idx].xyz;
}

float get_radius(int anchor_idx) {
    if (JA_FIX_IN_FRAME) {
        return radii[anchor_idx / 4][anchor_idx % 4] * JA_CAMERA_SCALED_FACTOR;
    }
    return radii[anchor_idx / 4][anchor_idx % 4];
}

vec4 get_color(int anchor_idx) {
    return colors[anchor_idx];
}

vec4 get_fill(int anchor_idx) {
    return fills[anchor_idx];
}

#endif

