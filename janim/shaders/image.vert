#version 330 core
layout (location = 0) in vec3 pos;
layout (location = 1) in vec4 color;
layout (location = 2) in vec2 tex_coords;

out vec2 v_tex_coords;

uniform mat4 view_matrix;
uniform mat4 proj_matrix;
uniform mat4 wnd_matrix;

void main()
{
	gl_Position = wnd_matrix * proj_matrix * view_matrix * vec4(pos, 1.0);
	v_tex_coords = tex_coords;
}
