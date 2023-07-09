#version 430 core
layout (location = 0) in vec3 aPos0;
layout (location = 1) in vec3 aPos1;
layout (location = 2) in vec3 aPos2;
layout (location = 3) in vec4 aColor0;
layout (location = 4) in vec4 aColor1;
layout (location = 5) in vec4 aColor2;

out vec4 v_pos[3];
out vec4 v_color[3];

uniform mat4 view_matrix;

void main()
{
    v_pos[0] = view_matrix * vec4(aPos0, 1.0);
    v_pos[1] = view_matrix * vec4(aPos1, 1.0);
    v_pos[2] = view_matrix * vec4(aPos2, 1.0);
    v_color[0] = aColor0;
    v_color[1] = aColor1;
    v_color[2] = aColor2;
}
