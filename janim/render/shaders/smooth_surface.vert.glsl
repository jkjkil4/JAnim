#version 330 core

in vec3 in_point;
in vec3 in_normal;

out vec3 v_point;
out vec3 v_normal;

uniform bool JA_FIX_IN_FRAME;
uniform mat4 JA_VIEW_MATRIX;
uniform float JA_FIXED_DIST_FROM_PLANE;
uniform mat4 JA_PROJ_MATRIX;

void main()
{
    v_point = in_point;
    v_normal = in_normal;
    if (JA_FIX_IN_FRAME) {
        gl_Position = vec4(in_point - vec3(0.0, 0.0, JA_FIXED_DIST_FROM_PLANE), 1.0);
    } else {
        gl_Position = JA_PROJ_MATRIX * JA_VIEW_MATRIX * vec4(in_point, 1.0); 
    }
    gl_Position.z *= 0.1;
}

