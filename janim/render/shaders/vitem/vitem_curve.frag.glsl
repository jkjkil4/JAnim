#version 430 core

in vec2 v_coord;

flat in int idx;
flat in int prev_idx;
flat in int next_idx;

out vec4 f_color;

uniform float JA_CAMERA_SCALED_FACTOR;
uniform float JA_ANTI_ALIAS_RADIUS;
uniform bool JA_FIX_IN_FRAME;

uniform vec4 glow_color;
uniform float glow_size;

const float INFINITY = uintBitsToFloat(0x7F800000);

#[JA_FINISH_UP_UNIFORMS]

layout(std140, binding = 0) buffer MappedPoints
{
    vec4 points[];  // vec4(x, y, depth, 0)
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

#include "distance_to_curve.glsl"
#include "vitem_curve_color.glsl"

#define FRAG_AREA

void main()
{
    float d = distance_to_curve(idx);
    float prev_d = distance_to_curve(prev_idx);
    float next_d = distance_to_curve(next_idx);

    if (prev_d < d || next_d < d) {
        #ifdef FRAG_AREA
        f_color = vec4(1.0, 0.0, 0.0, 0.5);
        return;
        #endif

        discard;
    }

    f_color = get_vitem_curve_color(d, idx);

    if (f_color.a == 0.0) {
        #ifdef FRAG_AREA
        f_color = vec4(1.0, 0.5, 0.0, 0.5);
        return;
        #endif

        discard;
    }

    #[JA_FINISH_UP]
}
