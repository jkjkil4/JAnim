#version 330 core

in vec3 in_point;
in vec4 in_color;
in float in_radius;

out vec4 v_pos;
out vec4 v_color;
out float v_radius;

uniform bool JA_FIX_IN_FRAME;
uniform mat4 JA_VIEW_MATRIX;
uniform float JA_FIXED_DIST_FROM_PLANE;
uniform mat4 JA_PROJ_MATRIX;

void main()
{
    if (JA_FIX_IN_FRAME) {
        v_pos = vec4(in_point - vec3(0.0, 0.0, JA_FIXED_DIST_FROM_PLANE), 1.0);
    } else {
        v_pos = JA_VIEW_MATRIX * vec4(in_point, 1.0);
    }
    v_color = in_color;
    v_radius = in_radius;
}
