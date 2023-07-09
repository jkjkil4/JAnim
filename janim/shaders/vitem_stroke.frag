#version 430 core

in vec4 color;

out vec4 FragColor;

void main()
{
    FragColor = color;
    // FragColor = vec4(1.0, 1.0, 1.0, 1.0);
}
