#version 330 core

in vec2 v_pos;

out vec4 FragColor;

uniform vec2 wnd_shape;
uniform vec2 xy_buff;
uniform int inv_step;

void main()
{
    if (v_pos.x > xy_buff.x && v_pos.x < 1.0 - xy_buff.x 
     && v_pos.y > xy_buff.y && v_pos.y < 1.0 - xy_buff.y)
        discard;

    int sum = int(v_pos.x * wnd_shape.x + v_pos.y * wnd_shape.y);
    if (sum % (2 * inv_step) < inv_step)
        discard;

    FragColor = vec4(1.0, 1.0, 1.0, 0.25);
}
