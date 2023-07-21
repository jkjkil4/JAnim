#version 330 core
layout (triangles) in;
layout (triangle_strip, max_vertices = 6) out;

in vec3 verts[3];
in vec4 v_color[3];
in float v_stroke_width[3];
in vec3 v_joint_info[3];

out vec2 uv_coords;
out vec4 color;
out float uv_stroke_width;
out float uv_anti_alias_width;
out float is_linear;

uniform float anti_alias_width;
uniform mat4 view_matrix;
uniform mat4 proj_matrix;
uniform mat4 wnd_matrix;

uniform vec3 vitem_unit_normal;
uniform int joint_type;

uniform float z_offset; // 用于保证 stroke 和 fill 的前后遮挡关系

const int AUTO_JOINT = 0;
const int BEVEL_JOINT = 1;
const int SHARP_JOINT = 2;

const float linear_tolerance_det = 0.01;

const float sharp_tolerance_dot = 0.866;

float sqr(float v)
{
    return v * v;
}

void create_joint(
    vec3 unit_normal, float buff,
    vec3 p0, vec3 p1, vec3 p2,
    vec3 static_c0, out vec3 changing_c0,
    vec3 static_c1, out vec3 changing_c1
) {
    vec3 v01 = normalize(p1 - p0);
    vec3 v12 = normalize(p2 - p1);
    if (
        joint_type == SHARP_JOINT || (
            joint_type == AUTO_JOINT && 
            dot(normalize(v01), normalize(-v12)) > sharp_tolerance_dot
    )) {
        changing_c0 = static_c0;
        changing_c1 = static_c1;
        return;
    }

    vec3 joint_normal = cross(-v01, v12);

    float orientation = sign(dot(unit_normal, joint_normal));

    float cos_angle = dot(v01, v12);
    float sin_angle = length(joint_normal);

    vec3 shift = orientation * buff * sin_angle / (1 + cos_angle) * v12;

    changing_c0 = static_c0 - shift;
    changing_c1 = static_c1 + shift;
}

vec2 xs_on_clean_parabola(vec3 b0, vec3 b1, vec3 b2)
{
    /*
    Given three control points for a quadratic bezier,
    this returns the two values (x0, x2) such that the
    section of the parabola y = x^2 between those values
    is isometric to the given quadratic bezier.

    Adapated from https://raphlinus.github.io/graphics/curves/2019/12/23/flatten-quadbez.html
    */
    vec3 dd = 2 * b1 - b0 - b2;

    float u0 = dot(b1 - b0, dd);
    float u2 = dot(b2 - b1, dd);
    float cp = length(cross(b2 - b0, dd));

    return vec2(u0 / cp, u2 / cp);
}


mat4 map_triangles(vec3 src0, vec3 src1, vec3 src2, vec3 dst0, vec3 dst1, vec3 dst2)
{
    /*
    Return an affine transform which maps the triangle (src0, src1, src2)
    onto the triangle (dst0, dst1, dst2)
    */
    mat4 src_mat = mat4(
        src0, 1.0,
        src1, 1.0,
        src2, 1.0,
        vec4(1.0)
    );
    mat4 dst_mat = mat4(
        dst0, 1.0,
        dst1, 1.0,
        dst2, 1.0,
        vec4(1.0)
    );
    return dst_mat * inverse(src_mat);
}


mat4 rotation(vec3 axis, float cos_angle)
{
    float c = cos_angle;
    float s = sqrt(1 - c * c);  // Sine of the angle
    float oc = 1.0 - c;
    float ax = axis.x;
    float ay = axis.y;
    float az = axis.z;

    return mat4(
        oc * ax * ax + c,      oc * ax * ay + az * s, oc * az * ax - ay * s, 0.0,
        oc * ax * ay - az * s, oc * ay * ay + c,      oc * ay * az + ax * s, 0.0,
        oc * az * ax + ay * s, oc * ay * az - ax * s, oc * az * az + c,      0.0,
        0.0, 0.0, 0.0, 1.0
    );
}


mat4 map_onto_x_axis(vec3 src0, vec3 src1)
{
    mat4 shift = mat4(1.0);
    shift[3].xyz = -src0;

    // Find rotation matrix between unit vectors in each direction    
    vec3 vect = normalize(src1 - src0);
    // No rotation needed
    if(vect.x > 1 - 1e-6) return shift;

    // Equivalent to cross(vect, vec3(1, 0, 0))
    vec3 axis = normalize(vec3(0.0, vect.z, -vect.y));
    mat4 rotate = rotation(axis, vect.x);
    return rotate * shift;
}


mat4 get_xyz_to_uv(
    vec3 b0, vec3 b1, vec3 b2,
    float threshold,
    out bool exceeds_threshold
) {
    /*
    Populates the matrix `result` with an affine transformation which maps a set of
    quadratic bezier controls points into a new coordinate system such that the bezier
    curve coincides with y = x^2.

    If the x-range under this part of the curve exceeds `threshold`, this returns false
    and populates result a matrix mapping b0 and b2 onto the x-axis
    */
    vec2 xs = xs_on_clean_parabola(b0, b1, b2);
    float x0 = xs[0];
    float x1 = 0.5 * (xs[0] + xs[1]);
    float x2 = xs[1];
    // Portions of the parabola y = x^2 where abs(x) exceeds
    // this value are treated as straight lines.
    exceeds_threshold = (min(x0, x2) > threshold || max(x0, x2) < -threshold);
    if(exceeds_threshold){
        return map_onto_x_axis(b0, b2);
    }
    // This triangle on the xy plane should be isometric
    // to (b0, b1, b2), and it should define a quadratic
    // bezier segment aligned with y = x^2
    vec3 dst0 = vec3(x0, x0 * x0, 0.0);
    vec3 dst1 = vec3(x1, x0 * x2, 0.0);
    vec3 dst2 = vec3(x2, x2 * x2, 0.0);
    return map_triangles(b0, b1, b2, dst0, dst1, dst2);
}

void main()
{
    if (v_stroke_width[0] == 0.0 && v_stroke_width[1] == 0.0 && v_stroke_width[2] == 0.0)
        return;

    vec3 handle_prev = v_joint_info[0];
    vec3 handle_next = v_joint_info[2];
    bool has_prev = bool(v_joint_info[1][0]);
    bool has_next = bool(v_joint_info[1][1]);

    // basic
    vec3 v10 = verts[0] - verts[1];
    vec3 v12 = verts[2] - verts[1];
    float unsigned_det = length(cross(normalize(v10), normalize(v12)));
    is_linear = float(unsigned_det < linear_tolerance_det && dot(v10, v12) < 0.0);

    vec3 unit_normal = 
        bool(is_linear)
        ? vitem_unit_normal
        : normalize(cross(v10, v12));
    vec3 p0_perp = vec3(0.5 * v_stroke_width[0] * normalize(cross(v10, unit_normal)));
    vec3 p2_perp = vec3(0.5 * v_stroke_width[2] * normalize(cross(unit_normal, v12)));
    vec3 p1_perp = (p0_perp + p2_perp) / 2.0;

    vec3 p0 = verts[0];
    vec3 p1 = verts[1];
    vec3 p2 = verts[2];

    // corners
    /*
        2--------4
        |        |
        |        5
        |     3
        0---1
    */
    vec3 corners[6];
    corners[0] = p0 + p0_perp;
    corners[1] = p0 - p0_perp;
    corners[2] = p1 + p1_perp;
    corners[3] = p1 - p1_perp;
    corners[4] = p2 + p2_perp;
    corners[5] = p2 - p2_perp;

    if (!bool(is_linear))
        corners[3] = (corners[1] + corners[5]) / 2.0;

    // joints
    // TODO: 为不在同一平面的曲线创建连接处
    // TODO: 将 SHARP_JOINT 完善为 ROUND_JOINT
    if (has_prev)
        create_joint(
            unit_normal, v_stroke_width[0] / 2.0,
            handle_prev, p0, p1,
            corners[0], corners[0],
            corners[1], corners[1]
        );
    if (has_next)
        create_joint(
            -unit_normal, v_stroke_width[2] / 2.0,
            handle_next, p2, p1,
            corners[4], corners[4],
            corners[5], corners[5]
        );

    // xyz_to_uv
    bool too_steep = false;
    mat4 xyz_to_uv;
    float uv_scale_factor;
    if (!bool(is_linear)) {
        xyz_to_uv = get_xyz_to_uv(p0, p1, p2, 2.0, too_steep);

        // uv_scale_factor = length(xyz_to_uv[0].xyz);

        // 这是如何起作用的？
        float f1 = length(xyz_to_uv[0].xyz);
        float f2 = length(xyz_to_uv[1].xyz);
        float f3 = length(xyz_to_uv[2].xyz);
        uv_scale_factor = f1 + f2 + f3 - min(f1, min(f2, f3)) - max(f1, max(f2, f3));

        is_linear = float(too_steep);
    }

    for (int i = 0; i < 6; i++) {
        vec4 v4_corner = vec4(corners[i], 1.0);
        vec4 view_corner = view_matrix * v4_corner;
        vec4 proj_corner = proj_matrix * view_corner;

        // 有无更好的方法计算 view_corner 到 proj_corner 的缩放系数？
        vec4 proj_corner_test = proj_matrix * (view_corner + vec4(1.0, 0.0, 0.0, 0.0));
        float proj_scale_factor = proj_corner_test.x / proj_corner_test.w - proj_corner.x / proj_corner.w;

        gl_Position = wnd_matrix * proj_corner;
        // Flip and scale to prevent premature clipping
        gl_Position.z = gl_Position.z * 0.1 + z_offset;

        float stroke_width = v_stroke_width[i / 2];
        float scaled_aaw = anti_alias_width / proj_scale_factor;

        if (bool(is_linear)) {
            if (too_steep) {
                uv_coords = (xyz_to_uv * v4_corner).xy;
            } else {
                float sgn = vec2(-1, 1)[i % 2];
                uv_coords = vec2(0, sgn * (0.5 * stroke_width));
            }
            color = v_color[i / 2];
            uv_stroke_width = stroke_width;
            uv_anti_alias_width = scaled_aaw;
        } else {
            uv_coords = (xyz_to_uv * v4_corner).xy;
            color = v_color[i / 2];
            uv_stroke_width = stroke_width * uv_scale_factor;
            uv_anti_alias_width = scaled_aaw * uv_scale_factor;
        }
        EmitVertex();
    }
    EndPrimitive();
}
