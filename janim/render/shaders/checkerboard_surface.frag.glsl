#version 330 core

in vec3 v_point;
in vec3 v_normal;

out vec4 f_color;

uniform vec4 u_color1;
uniform vec4 u_color2;
uniform int u_row_length;

#include "../includes/shade.glsl"

void main()
{
    int idx = gl_PrimitiveID / 2;
    int u = idx / u_row_length;
    int v = idx % u_row_length;
    
    bool flag = (u + v) % 2 != 0;
    f_color = flag ? u_color2 : u_color1;
    f_color.rgb = apply_light(f_color.rgb, v_point, v_normal);
}

