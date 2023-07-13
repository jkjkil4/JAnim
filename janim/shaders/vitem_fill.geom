#version 330 core
layout (triangles) in;
layout (triangle_strip, max_vertices = 3) out;

in vec3 verts[3];
in vec4 v_color[3];
in int v_idx[3];

out vec4 color;

uniform mat4 view_matrix;
uniform mat4 proj_matrix;
uniform mat4 wnd_matrix;

void main()
{
    for (int i = 0; i < 3; i++) {
        gl_Position = wnd_matrix * proj_matrix * view_matrix * vec4(verts[i], 1.0);
        if (v_idx[0] + 1 == v_idx[1] && v_idx[0] + 2 == v_idx[2]) {
            color = vec4(1.0, 0.5, 0.5, 1.0);
        } else {
            color = vec4(0.5, 0.5, 1.0, 1.0);
        }
        EmitVertex();
    }
    EndPrimitive();
}
