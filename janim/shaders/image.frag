#version 330 core

in vec4 v_color;
in vec2 v_tex_coords;

out vec4 FragColor;

uniform sampler2D image;

void main()
{
	FragColor = texture(image, v_tex_coords) * v_color;
}
