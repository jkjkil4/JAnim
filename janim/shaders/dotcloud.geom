#version 330 core
layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

in vec4 v_pos[1];

out vec4 pos;

uniform mat4 wnd_mul_proj_matrix;

void main() {
    pos = v_pos[0];
    for (int i = 0; i < 4; i++) {
        int x_index = 2 * (i % 2) - 1;
        int y_index = 2 * (i / 2) - 1;
        gl_Position = v_pos[0] + vec4(0.1 * x_index, 0.1 * y_index, 0.0, 0.0);
        gl_Position = wnd_mul_proj_matrix * gl_Position;
        EmitVertex();
    }
    EndPrimitive();
}