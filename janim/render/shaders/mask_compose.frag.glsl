#version 330 core

in vec2 v_texcoord;

out vec4 f_color;

uniform sampler2D content_tex;
uniform sampler2D mask_tex;
uniform float u_mask_alpha;
uniform float u_feather;
uniform float u_invert;
uniform vec2 u_tex_size;

#[JA_FINISH_UP_UNIFORMS]

// 9x9 高斯模糊预归一化
const int KERNEL_RADIUS = 4;
const float weights[5] = float[](
	0.20236, 0.17820, 0.12155, 0.06425, 0.02630
);

float sample_mask_blurred(vec2 uv)
{
	vec2 texel = 1.0 / u_tex_size;
	float result = 0.0;
	float total = 0.0;

	for (int y = -KERNEL_RADIUS; y <= KERNEL_RADIUS; y++) {
		for (int x = -KERNEL_RADIUS; x <= KERNEL_RADIUS; x++) {
			float w = weights[abs(x)] * weights[abs(y)];
			vec2 offset = vec2(float(x), float(y)) * texel * u_feather;
			result += texture(mask_tex, uv + offset).a * w;
			total += w;
		}
	}

	return result / total;
}

void main()
{
	vec4 content_color = texture(content_tex, v_texcoord);

	// 采样蒙版值
	float mask_val;
	if (u_feather > 0.0) {
		mask_val = sample_mask_blurred(v_texcoord);
	} else {
		mask_val = texture(mask_tex, v_texcoord).a;
	}

	// 应用反转
	float effective_mask = mix(mask_val, 1.0 - mask_val, u_invert);

	// 应用透明度
	effective_mask = mix(1.0, effective_mask, u_mask_alpha);

	f_color = content_color * vec4(1.0, 1.0, 1.0, effective_mask);

	#[JA_FINISH_UP]
}
