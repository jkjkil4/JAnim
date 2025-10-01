#version 330 core
layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

in vec4 v_pos[1];
in vec4 v_color[1];
in float v_radius[1];

out vec2 g_center;
out vec4 g_color;
out float g_radius;
out vec2 g_point;

uniform mat4 JA_PROJ_MATRIX;
uniform vec2 JA_FRAME_RADIUS;
uniform float JA_ANTI_ALIAS_RADIUS;

uniform vec4 glow_color;
uniform float glow_size;

vec4 normalize_w(vec4 vect)
{
    return vect / vect.w;
}

void main()
{
    float inner_factor = 1.0;
    float radius = v_radius[0];
    if (glow_color.a > 0.0) {
        inner_factor = radius / (radius + glow_size);
        radius += glow_size;
    }
    vec4 corners[4];
    for (int i = 0; i < 4; i++) {
        vec2 direction = vec2(
            2 * (i % 2) - 1,
            2 * (i / 2) - 1
        );
        corners[i] = v_pos[0];
        corners[i].xy += radius * direction;
        corners[i] = normalize_w(JA_PROJ_MATRIX * corners[i]);
        corners[i].xy *= JA_FRAME_RADIUS;
        corners[i].xy += JA_ANTI_ALIAS_RADIUS * direction;
    }

    g_center = normalize_w(JA_PROJ_MATRIX * v_pos[0]).xy * JA_FRAME_RADIUS;
    g_color = v_color[0];
    g_radius = (corners[1].x - corners[0].x) / 2.0 - JA_ANTI_ALIAS_RADIUS;
    g_radius *= inner_factor;

    for (int i = 0; i < 4; i++) {
        g_point = corners[i].xy;
        gl_Position = corners[i];
        gl_Position.xy /= JA_FRAME_RADIUS;
        gl_Position.z *= 0.1;
        EmitVertex();
    }
    EndPrimitive();
}
