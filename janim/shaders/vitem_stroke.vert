#version 330 core
layout (location = 0) in vec3 point;
layout (location = 1) in vec4 color;
layout (location = 2) in float stroke_width;

// Bezier control point
out vec3 verts;
out vec4 v_color;
out float v_stroke_width;

void main()
{
    verts = point;
    v_color = color;
    v_stroke_width = stroke_width;
}
