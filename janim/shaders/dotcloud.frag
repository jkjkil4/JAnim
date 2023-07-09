#version 330 core
out vec4 FragColor;

in vec2 center;
in vec4 color;
in float radius;
in vec2 point;

uniform float anti_alias_width;

void main()
{
    vec2 diff = point - center;
    float dist = length(diff);
    float signed_dist = dist - radius;
    if (signed_dist > 0) 
        discard;
    FragColor = color;
    FragColor.a *= smoothstep(0.0, -1.0, signed_dist / anti_alias_width);
}