#version 430 core

layout(points) in;
layout(triangle_strip, max_vertices = 8) out;

in int v_prev_idx[1];
in int v_next_idx[1];

out vec2 v_coord;
out vec4 v_color;

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

#include "../../includes/is_approx_line.glsl"

void emit_coord(vec2 coord, float depth)
{
    v_coord = coord;
    gl_Position = vec4(v_coord / JA_FRAME_RADIUS, depth * 0.1, 1.0);
    EmitVertex();
}

// 对于曲线，如果 inverse = true，则说明结束的点在曲线左侧，否则在右侧

bool emit_points_near_control_right(int idx, float expand_radius)
{
    vec3 A = get_point_with_depth(idx);
    vec3 B = get_point_with_depth(idx + 1);
    vec3 C = get_point_with_depth(idx + 2);

    if (is_approx_line(A.xy, B.xy, C.xy)) {
        // 不直接使用 B，是为了避免 B 和 A 或 C 重合的情况
        vec3 center = (A + C) * 0.5;
        vec2 vec = expand_radius * rotate_90_ccw(normalize(C.xy - A.xy));

        emit_coord(center.xy + vec, center.z);
        emit_coord(center.xy - vec, center.z);
        return false;
    } else {
        vec2 v1 = B.xy - A.xy, v2 = C.xy - B.xy;
        vec2 sum_vec = -v1 + v2;
        vec2 expand_vec = expand_radius * normalize(sum_vec);
        float det = cross2d(v1, v2);

        emit_coord(B.xy - expand_vec, B.z);
        emit_coord(B.xy + sum_vec * 0.5 + expand_vec, B.z);

        vec2 rot_vec = normalize(det < 0 ? rotate_90_ccw(v2) : rotate_90_cw(v2));
        emit_coord(B.xy + rot_vec * expand_radius, B.z);
        return det < 0;
    }
}

void emit_points_near_control_left(int idx, float expand_radius, bool inverse)
{
    vec3 A = get_point_with_depth(idx);
    vec3 B = get_point_with_depth(idx + 1);
    vec3 C = get_point_with_depth(idx + 2);

    if (is_approx_line(A.xy, B.xy, C.xy)) {
        // 不直接使用 B，是为了避免 B 和 A 或 C 重合的情况
        vec3 center = (A + C) * 0.5;
        vec2 vec = expand_radius * rotate_90_ccw(normalize(C.xy - A.xy));

        if (inverse) {
            vec = -vec;
        }
        emit_coord(center.xy + vec, center.z);
        emit_coord(center.xy - vec, center.z);
    } else {
        vec2 v1 = B.xy - A.xy, v2 = C.xy - B.xy;
        vec2 sum_vec = -v1 + v2;
        vec2 expand_vec = expand_radius * normalize(sum_vec);
        float det = cross2d(v1, v2);

        vec2 rot_vec = normalize(det < 0 ? rotate_90_ccw(v1) : rotate_90_cw(v1));

        if (inverse == (det < 0)) {
            emit_coord(B.xy + sum_vec * 0.5 + expand_vec, B.z);
            emit_coord(B.xy + rot_vec * expand_radius, B.z);
            emit_coord(B.xy - expand_vec, B.z);
        } else {
            emit_coord(B.xy + rot_vec * expand_radius, B.z);
            emit_coord(B.xy + sum_vec * 0.5 + expand_vec, B.z);
            emit_coord(B.xy - expand_vec, B.z);
        }
    }
}

void emit_points_near_anchor(float expand_radius, bool inverse)
{
    vec3 p0 = get_point_with_depth(prev_idx);
    vec3 p1 = get_point_with_depth(prev_idx + 1);
    vec3 p2 = get_point_with_depth(next_idx);
    vec3 p3 = get_point_with_depth(next_idx + 1);
    vec3 p4 = get_point_with_depth(next_idx + 2);
    if (p1 == p0 || p1 == p2) {
        p1 = (p0 + p2) * 0.5;
    }
    if (p3 == p4 || p3 == p2) {
        p3 = (p4 + p2) * 0.5;
    }

    if (is_approx_line(p1.xy, p2.xy, p3.xy)) {
        vec2 vec = expand_radius * rotate_90_ccw(normalize(p3.xy - p2.xy));

        if (inverse) {
            vec = -vec;
        }
        emit_coord(p2.xy + vec, p2.z);
        emit_coord(p2.xy - vec, p2.z);
    } else {
        vec2 v1 = normalize(p2.xy - p1.xy), v2 = normalize(p3.xy - p2.xy);
        vec2 v = normalize(-v1 + v2);
        float det = cross2d(v1, v2);
        if (inverse != (det < 0)) {
            v = -v;
        }

        float cos_value = dot(v2, v);
        float sin_value = sqrt(1.0 - cos_value * cos_value);
        float dist = expand_radius / sin_value;

        emit_coord(p2.xy + v * dist, p2.z);
        emit_coord(p2.xy - v * dist, p2.z);
    }
}

void emit_points_at_start(int idx, float expand_radius)
{

}

void emit_points_at_end(int idx, float expand_radius, bool inverse)
{

}

void main()
{
    prev_idx = v_prev_idx[0];
    next_idx = v_next_idx[0];

    v_color = mix(vec4(1.0, 0.0, 0.0, 1.0), vec4(0.0, 1.0, 0.0, 1.0), next_idx / 14.0);

    if (prev_idx == -1) {
        int next_anchor_idx = next_idx / 2;

        float expand_radius = max(get_radius(next_anchor_idx), get_radius(next_anchor_idx + 1));
        if (glow_color.a != 0.0) {
            expand_radius = max(expand_radius, glow_size);
        }
        expand_radius += JA_ANTI_ALIAS_RADIUS;

        emit_points_at_start(next_idx, expand_radius);
        emit_points_near_control_left(next_idx, expand_radius, false);
    } else if (next_idx == -1) {
        int prev_anchor_idx = prev_idx / 2;

        float expand_radius = max(get_radius(prev_anchor_idx), get_radius(prev_anchor_idx + 1));
        if (glow_color.a != 0.0) {
            expand_radius = max(expand_radius, glow_size);
        }
        expand_radius += JA_ANTI_ALIAS_RADIUS;

        bool flag = emit_points_near_control_right(prev_idx, expand_radius);
        emit_points_at_end(prev_idx, expand_radius, flag);
    } else {
        int prev_anchor_idx = prev_idx / 2;
        int next_anchor_idx = next_idx / 2;

        vec3 r = vec3(
            get_radius(prev_anchor_idx),
            get_radius(next_anchor_idx),
            get_radius(next_anchor_idx + 1)
        );
        if (glow_color.a != 0.0) {
            r = max(r, glow_size);
        }
        r += JA_ANTI_ALIAS_RADIUS;

        bool flag = emit_points_near_control_right(prev_idx, max(r.x, r.y));
        emit_points_near_anchor(r.y, flag);
        emit_points_near_control_left(next_idx, max(r.y, r.z), flag);
    }
    EndPrimitive();
}
