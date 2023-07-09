#version 430 core
layout (points) in;
layout (triangle_strip, max_vertices = 3) out;

in vec4 v_pos[1][3];
in vec4 v_color[1][3];

out vec4 color;

uniform float anti_alias_width;
uniform mat4 proj_matrix;
uniform mat4 wnd_matrix;

// bool find_intersection(vec2 p0, vec2 v0, vec2 p1, vec2 v1, out vec2 intersection){
//     // Find the intersection of a line passing through
//     // p0 in the direction v0 and one passing through p1 in
//     // the direction p1.
//     // That is, find a solutoin to p0 + v0 * t = p1 + v1 * s
//     float det = -v0.x * v1.y + v1.x * v0.y;
//     if(det == 0) return false;
//     float t = cross2d(p0 - p1, v1) / det;
//     intersection = p0 + v0 * t;
//     return true;
// }

void main()
{
    mat4 wnd_mul_proj_matrix = wnd_matrix * proj_matrix;
    vec4 wnd_pos[3];
    for (int i = 0; i < 3; i++) {
        wnd_pos[i] = wnd_mul_proj_matrix * v_pos[0][i];
    }
    for (int i = 0; i < 3; i++) {
        gl_Position = wnd_mul_proj_matrix * v_pos[0][i];
        color = v_color[0][i];
        EmitVertex();
    }
    EndPrimitive();
}
