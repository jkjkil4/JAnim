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

uniform mat4 proj_matrix;
uniform mat4 wnd_matrix;

vec4 normalize_w(vec4 vect) 
{
    return vect / vect.w;
}

void main()
{
    vec4 corners[4];
    for (int i = 0; i < 4; i++) {
        int xx = 2 * (i % 2) - 1;
        int yy = 2 * (i / 2) - 1;
        corners[i] = v_pos[0] + vec4(v_radius[0] * xx, v_radius[0] * yy, 0.0, 0.0);
        corners[i] = normalize_w(proj_matrix * corners[i]);
    }

    center = normalize_w(proj_matrix * v_pos[0]).xy;
    color = v_color[0];
    radius = (corners[1].x - corners[0].x) / 2.0;

    for (int i = 0; i < 4; i++) {
        point = corners[i].xy;
        gl_Position = wnd_matrix * corners[i];
        EmitVertex();
    }
    EndPrimitive();
}