#version 330 core
layout (location = 0) in vec3 point;
layout (location = 1) in vec4 color;
layout (location = 2) in float stroke_width;
layout (location = 3) in float handle_prev_coord;
layout (location = 4) in float handle_next_coord;

// Bezier control point
out vec3 verts;
out vec4 v_color;
out float v_stroke_width;
out float v_handle_prev;
out float v_handle_next;

void main()
{
    verts = point;
    v_color = color;
    v_stroke_width = stroke_width;
    v_handle_prev = handle_prev_coord;
    v_handle_next = handle_next_coord;
}
