#version 330 core

in vec2 in_coord;

out vec2 v_coord;

uniform vec2 JA_FRAME_RADIUS;

void main()
{
    gl_Position = vec4(in_coord, 0.0, 1.0);

    v_coord = in_coord * JA_FRAME_RADIUS;
}
