// Required:
//  v_coord

uniform vec3 JA_CAMERA_LOC;
uniform vec3 JA_CAMERA_CENTER;
uniform vec3 JA_CAMERA_RIGHT;
uniform vec3 JA_CAMERA_UP;

uniform mat4 JA_VIEW_MATRIX;
uniform mat4 JA_PROJ_MATRIX;

uniform vec3 unit_normal;
uniform vec3 start_point;
uniform bool DEPTH_TEST;

void compute_depth_if_needed()
{
    if (!DEPTH_TEST)
        return;

    // 像素在摄像机画面上的位置
    vec3 pixel_pos = JA_CAMERA_CENTER + JA_CAMERA_RIGHT * v_coord.x + JA_CAMERA_UP * v_coord.y;

    // 求解从摄像机位置发出的射线与平面的交点
    vec3 ray = pixel_pos - JA_CAMERA_LOC;
    float t = dot(unit_normal, start_point - JA_CAMERA_LOC) / dot(unit_normal, ray);
    vec3 p = JA_CAMERA_LOC + ray * t;

    // 计算深度值
    vec4 clip_space_pos = JA_PROJ_MATRIX * JA_VIEW_MATRIX * vec4(p, 1.0);
    float ndc_depth = clip_space_pos.z / clip_space_pos.w * 0.1;
    gl_FragDepth = (ndc_depth + 1.0) / 2.0;
}
