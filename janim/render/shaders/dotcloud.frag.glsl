#version 330 core

in vec2 g_center;
in vec4 g_color;
in float g_radius;
in vec2 g_point;

out vec4 f_color;

uniform float JA_ANTI_ALIAS_RADIUS;

void main()
{
    vec2 diff = g_point - g_center;
    float dist = length(diff);
    float signed_dist = dist - g_radius;
    if (signed_dist > JA_ANTI_ALIAS_RADIUS)
        discard;
    f_color = g_color;
    f_color.a *= smoothstep(1, -1, signed_dist / JA_ANTI_ALIAS_RADIUS);
}
