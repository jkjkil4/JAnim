// GLSL 对于未使用变量会自动静默移除
// 所以不用担心未使用到的冗余定义

uniform bool JA_FIX_IN_FRAME;

uniform float JA_CAMERA_SCALED_FACTOR;
uniform vec3 JA_CAMERA_CENTER;
uniform vec3 JA_CAMERA_LOC;
uniform vec3 JA_CAMERA_RIGHT;
uniform vec3 JA_CAMERA_UP;
uniform mat4 JA_VIEW_MATRIX;
uniform float JA_FIXED_DIST_FROM_PLANE;
uniform mat4 JA_PROJ_MATRIX;
uniform vec2 JA_FRAME_RADIUS;
uniform float JA_ANTI_ALIAS_RADIUS;
uniform vec3 JA_LIGHT_SOURCE;
