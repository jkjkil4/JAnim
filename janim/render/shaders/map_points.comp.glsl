#version 430 core

layout(local_size_x = 256) in;

layout(std140, binding = 0) buffer InputBuffer {
    vec4 points[];      // (x, y, z, isclosed)
};

layout(std140, binding = 1) buffer OutputBuffer {
    vec4 mapped_points[];     // (x, y, isclosed, 0)
};

uniform bool JA_FIX_IN_FRAME;
uniform mat4 JA_VIEW_MATRIX;
uniform mat4 JA_PROJ_MATRIX;
uniform float JA_FIXED_DIST_FROM_PLANE;
uniform vec2 JA_FRAME_RADIUS;

void main() {
    uint index = gl_GlobalInvocationID.x;

    vec4 point;
    if (JA_FIX_IN_FRAME) {
        point = JA_PROJ_MATRIX * vec4(points[index].xy, points[index].z - JA_FIXED_DIST_FROM_PLANE, 1.0);
    } else {
        point = JA_PROJ_MATRIX * JA_VIEW_MATRIX * vec4(points[index].xyz, 1.0);
    }
    mapped_points[index].xy = (point.xy / point.w) * JA_FRAME_RADIUS;
    mapped_points[index].z = points[index].w;
}