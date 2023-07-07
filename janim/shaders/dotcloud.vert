#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec4 aColor;

out vec4 v_pos;
out vec4 v_color;

uniform mat4 view_matrix;

void main()
{
    v_pos = view_matrix * vec4(aPos, 1.0);
    v_color = aColor;
}
