#version 330 core

in vec2 v_texcoord;

out vec4 f_color;

uniform sampler2D u_fbo;

#[JA_FINISH_UP_UNIFORMS]

void main()
{
    f_color = texture(u_fbo, v_texcoord);

    #[JA_FINISH_UP]
}

