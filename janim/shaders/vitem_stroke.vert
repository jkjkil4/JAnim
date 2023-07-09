#version 330 core
layout (location = 0) in vec3 point;
layout (location = 1) in vec4 color;
layout (location = 2) in float stroke_width;

// Bezier control point
out vec4 verts;
out vec4 v_color;
out float v_stroke_width;

uniform mat4 view_matrix;

void main()
{
    verts = view_matrix * vec4(point, 1.0);
    v_color = color;
    v_stroke_width = stroke_width;
}
