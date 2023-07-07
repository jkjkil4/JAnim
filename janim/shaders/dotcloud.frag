#version 330 core
out vec4 FragColor;

in vec4 pos;

void main()
{
    FragColor = vec4(pos.x + 0.5, pos.y + 0.5, 0.0, 1.0);
}