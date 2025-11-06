#version 430 core

layout(points) in;
layout(triangle_strip, max_vertices = 6) out;

in int v_idx[1];
in int v_prev_idx[1];
in int v_next_idx[1];

out vec2 v_coord;

flat out int idx;
flat out int prev_idx;
flat out int next_idx;

uniform float JA_CAMERA_SCALED_FACTOR;
uniform vec2 JA_FRAME_RADIUS;
uniform float JA_ANTI_ALIAS_RADIUS;
uniform bool JA_FIX_IN_FRAME;

uniform vec4 glow_color;
uniform float glow_size;

layout(std140, binding = 0) buffer MappedPoints
{
    vec4 points[];  // vec4(x, y, depth, 0)
};

layout(std140, binding = 1) buffer Radii
{
    vec4 radii[];   // radii[idx / 4][idx % 4]
};

vec3 get_point_with_depth(int idx) {
    return points[idx].xyz;
}

float get_radius(int anchor_idx) {
    if (JA_FIX_IN_FRAME) {
        return radii[anchor_idx / 4][anchor_idx % 4] * JA_CAMERA_SCALED_FACTOR;
    }
    return radii[anchor_idx / 4][anchor_idx % 4];
}

vec2 rotate_90_ccw(vec2 v) {
    return vec2(-v.y, v.x);
}

vec2 rotate_90_cw(vec2 v) {
    return vec2(v.y, -v.x);
}

float cross2d(vec2 a, vec2 b) {
    return a.x * b.y - a.y * b.x;
}

void main()
{
    idx = v_idx[0];
    prev_idx = v_prev_idx[0];
    next_idx = v_next_idx[0];

    int anchor_idx = idx / 2;
    vec3 A = get_point_with_depth(idx);
    vec3 B = get_point_with_depth(idx + 1);
    vec3 C = get_point_with_depth(idx + 2);
    if (A == B || B == C) {
        B = (A + C) * 0.5;
    }

    float expand_radius = max(get_radius(anchor_idx), get_radius(anchor_idx + 1));
    if (glow_color.a != 0.0) {
        expand_radius = max(expand_radius, glow_size);
    }
    expand_radius += JA_ANTI_ALIAS_RADIUS;
    expand_radius += 0.05;

    vec2 v1 = normalize(B.xy - A.xy);
    vec2 v2 = normalize(C.xy - B.xy);

    vec2 A_base = A.xy - v1 * expand_radius;
    vec2 C_base = C.xy + v2 * expand_radius;

    vec2 A_offset = rotate_90_cw(v1) * expand_radius;
    vec2 B_offset1 = rotate_90_cw(v1) * expand_radius;
    vec2 B_offset2 = rotate_90_cw(v2) * expand_radius;
    vec2 C_offset = rotate_90_ccw(v2) * expand_radius;

    if (cross2d(v1, v2) < 0.0) {
        A_offset = -A_offset;
        B_offset1 = -B_offset1;
        B_offset2 = -B_offset2;
        C_offset = -C_offset;
    }

    v_coord = A_base + A_offset;
    gl_Position = vec4(v_coord / JA_FRAME_RADIUS, A.z * 0.1, 1.0);
    EmitVertex();

    v_coord = A_base - A_offset;
    gl_Position = vec4(v_coord / JA_FRAME_RADIUS, A.z * 0.1, 1.0);
    EmitVertex();

    v_coord = B.xy + B_offset1;
    gl_Position = vec4(v_coord / JA_FRAME_RADIUS, B.z * 0.1, 1.0);
    EmitVertex();

    v_coord = C_base + C_offset;
    gl_Position = vec4(v_coord / JA_FRAME_RADIUS, C.z * 0.1, 1.0);
    EmitVertex();

    v_coord = B.xy + B_offset2;
    gl_Position = vec4(v_coord / JA_FRAME_RADIUS, B.z * 0.1, 1.0);
    EmitVertex();

    v_coord = C_base - C_offset;
    gl_Position = vec4(v_coord / JA_FRAME_RADIUS, C.z * 0.1, 1.0);
    EmitVertex();

    EndPrimitive();
}
