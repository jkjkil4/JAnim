#version 330 core

in vec3 in_point;
in vec4 in_color;
in float in_radius;

out vec4 v_pos;
out vec4 v_color;
out float v_radius;

uniform mat4 JA_VIEW_MATRIX;
uniform mat4 JA_PROJ_MATRIX;

void main()
{
    v_pos = JA_VIEW_MATRIX * vec4(in_point, 1.0);
    v_color = in_color;
    v_radius = in_radius;
}
