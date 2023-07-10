#version 330 core
layout (location = 0) in vec3 pos;
layout (location = 1) in vec4 color;
layout (location = 2) in float radius;

out vec4 v_pos;
out vec4 v_color;
out float v_radius;

uniform mat4 view_matrix;

void main()
{
    v_pos = view_matrix * vec4(pos, 1.0);
    v_color = color;
    v_radius = radius;
}
