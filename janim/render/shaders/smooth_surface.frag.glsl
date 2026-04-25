#version 330 core

in vec3 v_point;
in vec3 v_normal;

out vec4 f_color;

uniform vec4 u_color;

#include "../includes/shade.glsl"

void main()
{
    f_color = u_color;
    f_color.rgb += get_shade(v_point, v_normal); 
}

