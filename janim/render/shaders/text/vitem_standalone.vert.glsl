in vec2 in_coord;
in vec2 in_texcoord;

out vec2 v_coord;

void main()
{
    v_coord = in_coord;
    gl_Position = vec4((in_texcoord - 0.5) * 2, 0.0, 1.0);
}

