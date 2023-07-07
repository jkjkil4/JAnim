#version 330 core
layout (location = 0) in vec3 aPos;

out vec4 v_pos;

uniform mat4 view_matrix;

void main()
{
    v_pos = view_matrix * vec4(aPos, 1.0);
}
