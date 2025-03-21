#version 330 core

in vec4 v_color;
in vec2 v_texcoord;

out vec4 f_color;

uniform sampler2D image;

// used by JA_FINISH_UP
uniform bool JA_BLENDING;
uniform sampler2D JA_FRAMEBUFFER;

void main()
{
	f_color = texture(image, v_texcoord) * v_color;

	#[JA_FINISH_UP]
}
