#version 330 core
layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

in vec4 v_pos[1];
in vec4 v_color[1];
in float v_radius[1];

out vec2 center;
out vec4 color;
out float radius;
out vec2 point;

uniform float anti_alias_width;
uniform mat4 wnd_mul_proj_matrix;

void main()
{
    center = v_pos[0].xy;
    color = v_color[0];
    radius = v_radius[0];

    float rpa = radius + anti_alias_width;
    for (int i = 0; i < 4; i++) {
        int xx = 2 * (i % 2) - 1;
        int yy = 2 * (i / 2) - 1;
        vec4 corner = v_pos[0] + vec4(rpa * xx, rpa * yy, 0.0, 0.0);
        gl_Position = wnd_mul_proj_matrix * corner;
        point = corner.xy;
        EmitVertex();
    }
    EndPrimitive();
}