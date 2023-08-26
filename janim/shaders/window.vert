#version 330 core
layout (location = 0) in vec2 pos;

out vec2 v_pos;

void main() 
{
    v_pos = pos;
    gl_Position = vec4(pos.x * 2.0 - 1.0, pos.y * 2.0 - 1.0, 0.0, 1.0);
}