#version 330 core

in vec2 g_center;
in vec4 g_color;
in float g_radius;
in vec2 g_point;

out vec4 f_color;

uniform float JA_ANTI_ALIAS_RADIUS;

#[JA_FINISH_UP_UNIFORMS]

uniform vec4 glow_color;
uniform float glow_size;

#include "../includes/blend_color.glsl"

void main()
{
    vec2 diff = g_point - g_center;
    float dist = length(diff);
    float sgn_d = dist - g_radius;

    if (glow_color.a > 0.0) {
        if (sgn_d > glow_size)
            discard;
    } else {
        if (sgn_d > JA_ANTI_ALIAS_RADIUS)
            discard;
    }

    f_color = g_color;
    f_color.a *= smoothstep(1, -1, sgn_d / JA_ANTI_ALIAS_RADIUS);

    if (glow_color.a > 0.0) {
        float factor;
        if (sgn_d >= 0) {
            factor = 1 - sgn_d / glow_size;
        } else {
            factor = 1 - (-sgn_d) / JA_ANTI_ALIAS_RADIUS / 2;
        }
        if (0 < factor && factor <= 1) {
            vec4 f_glow_color = glow_color;
            f_glow_color.a *= factor * factor;
            f_color = blend_color(f_color, f_glow_color);
        }
    }

    #[JA_FINISH_UP]
}
