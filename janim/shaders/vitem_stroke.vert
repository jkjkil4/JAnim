#version 330 core
layout (location = 0) in vec3 point;
layout (location = 1) in vec4 color;
layout (location = 2) in float stroke_width;
layout (location = 3) in vec3 joint_info;

// Bezier control point
out vec3 verts;
out vec4 v_color;
out float v_stroke_width;
out vec3 v_joint_info;

void main()
{
    verts = point;
    v_color = color;
    v_stroke_width = stroke_width;
    v_joint_info = joint_info;
}
