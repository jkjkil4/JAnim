#version 330 core

in vec4 v_color;
in vec2 v_texcoord;

out vec4 f_color;

uniform sampler2D image;

#[JA_FINISH_UP_UNIFORMS]

void main()
{
	f_color = texture(image, v_texcoord) * v_color;

	#[JA_FINISH_UP]
}
