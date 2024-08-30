#version 330 core
in vec3 in_point;
in vec4 in_color;
in vec2 in_texcoord;

out vec4 v_color;
out vec2 v_texcoord;

uniform bool JA_FIX_IN_FRAME;
uniform mat4 JA_VIEW_MATRIX;
uniform float JA_FIXED_DIST_FROM_PLANE;
uniform mat4 JA_PROJ_MATRIX;

void main()
{
	if (JA_FIX_IN_FRAME) {
		gl_Position = JA_PROJ_MATRIX * vec4(in_point.xy, in_point.z - JA_FIXED_DIST_FROM_PLANE, 1.0);
	} else {
		gl_Position = JA_PROJ_MATRIX * JA_VIEW_MATRIX * vec4(in_point, 1.0);
	}
	gl_Position.z *= 0.1;
	v_color = in_color;
	v_texcoord = in_texcoord;
}
