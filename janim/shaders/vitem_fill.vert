#version 330 core
layout (location = 0) in vec3 point;
layout (location = 1) in vec4 color;

out vec3 verts;
out vec4 v_color;
out int v_idx;

void main()
{
    verts = point;
    color = color;
    idx = gl_VertexID;
}
