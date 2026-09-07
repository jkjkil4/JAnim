#version 330 core

in vec2 in_coord;
in vec2 in_texcoord;

out vec2 v_texcoord;

#include "../../includes/janim_globals.glsl"

uniform float u_scale;
uniform vec2 u_char_orig;
uniform mat2 u_char_mat;

void main()
{
    vec2 frame_pos = u_char_mat * (in_coord / u_scale) + u_char_orig;
    v_texcoord = in_texcoord;
    gl_Position = vec4(frame_pos / JA_FRAME_RADIUS, 0.0, 1.0);
}
