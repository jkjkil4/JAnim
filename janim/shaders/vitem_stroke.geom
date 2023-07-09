#version 430 core
layout (points) in;
layout (triangle_strip, max_vertices = 5) out;

in vec4 v_pos[1][3];
in vec4 v_color[1][3];
in vec2 v_stroke_width[1];

out vec4 point;
out vec4 color;

uniform float anti_alias_width;
uniform mat4 proj_matrix;
uniform mat4 wnd_matrix;

const float tolerance_det = 0.01;
const int color_idx[5] = { 0, 0, 1, 2, 2 };

float cross2d(vec2 v, vec2 w)
{
    return v.x * w.y - w.x * v.y;
}

vec4 normalize_w(vec4 vect) 
{
    return vect / vect.w;
}

vec2 find_intersection(vec2 p0, vec2 v0, vec2 p1, vec2 v1)
{
    // Find the intersection of a line passing through
    // p0 in the direction v0 and one passing through p1 in
    // the direction p1.
    // That is, find a solutoin to p0 + v0 * t = p1 + v1 * s
    float det = -v0.x * v1.y + v1.x * v0.y;
    float t = cross2d(p0 - p1, v1) / det;
    return p0 + v0 * t;
}

void legacy() {
    mat4 wnd_mul_proj_matrix = wnd_matrix * proj_matrix;
    // vec4 wnd_pos[3];
    // for (int i = 0; i < 3; i++) {
    //     wnd_pos[i] = wnd_mul_proj_matrix * v_pos[0][i];
    // }
    for (int i = 0; i < 3; i++) {
        gl_Position = wnd_mul_proj_matrix * v_pos[0][i];
        color = v_color[0][i];
        EmitVertex();
    }
    EndPrimitive();
}

void main()
{
    vec4 proj_pos[3];
    for (int i = 0; i < 3; i++) {
        proj_pos[i] = normalize_w(proj_matrix * v_pos[0][i]);
    }

    vec2 v10 = proj_pos[0].xy - proj_pos[1].xy;
    vec2 v12 = proj_pos[2].xy - proj_pos[1].xy;
    vec4 v10_perp = vec4(normalize(vec2(-v10.y, v10.x)) * v_stroke_width[0][0], 0.0, 0.0);
    vec4 v12_perp = vec4(normalize(vec2(-v12.y, v12.x)) * v_stroke_width[0][1], 0.0, 0.0);

    vec4 vert[5];
    float det = cross2d(normalize(v10), normalize(v12));
    if (abs(det) < tolerance_det && dot(v10, v12) < 0.0) {
        /*
            0---2---4
            |       |
            1---o---3
        */
        vert[0] = proj_pos[0] - v10_perp;
        vert[1] = proj_pos[0] + v10_perp;
        vert[3] = proj_pos[2] - v12_perp;
        vert[4] = proj_pos[2] + v12_perp;

        vert[2] = (vert[0] + vert[4]) / 2.0;
    } else {
        if (det > 0.0) {  // right-turn
            /*
                2--------4
                |        |
                |        3
                |     .
                0---1
            */
            vert[0] = proj_pos[0] - v10_perp;
            vert[1] = proj_pos[0] + v10_perp;
            vert[3] = proj_pos[2] - v12_perp;
            vert[4] = proj_pos[2] + v12_perp;

            vert[2] = vec4(find_intersection(vert[0].xy, v10, vert[4].xy, v12), proj_pos[1].z, 1.0);
        } else {        // left-turn
            /*
                4--------2
                |        |
                3        |
                .     |
                    1---0
            */
            vert[0] = proj_pos[0] + v10_perp;
            vert[1] = proj_pos[0] - v10_perp;
            vert[3] = proj_pos[2] + v12_perp;
            vert[4] = proj_pos[2] - v12_perp;

            vert[2] = vec4(find_intersection(vert[0].xy, v10, vert[4].xy, v12), proj_pos[1].z, 1.0);
        }
    }

    for (int i = 0; i < 5; i++) {
        gl_Position = wnd_matrix * vert[i];
        color = v_color[0][color_idx[i]];
        EmitVertex();
    }
    EndPrimitive();
}
