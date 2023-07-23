#version 330 core
layout (triangles) in;
layout (triangle_strip, max_vertices = 3) out;

in vec3 verts[3];
in vec4 v_color[3];
in int v_idx[3];

out vec2 uv_coords;
out vec4 color;
out float is_corner;
out float is_convex;
out float uv_anti_alias_width;

uniform float anti_alias_width;

uniform mat4 view_matrix;
uniform mat4 proj_matrix;
uniform mat4 wnd_matrix;

uniform vec3 vitem_unit_normal;

const float linear_tolerance_det = 0.01;


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
    if (v_color[0][3] == 0.0 && v_color[1][3] == 0.0 && v_color[2][3] == 0.0)
        return;

    is_corner = float(v_idx[0] % 3 == 0 &&  v_idx[0] + 1 == v_idx[1] && v_idx[0] + 2 == v_idx[2]);
    if (bool(is_corner)) {
        vec3 v10 = verts[0] - verts[1];
        vec3 v12 = verts[2]- verts[1];
        vec3 curve_normal = cross(normalize(-v10), normalize(v12));
        float unsigned_det = length(curve_normal);
        bool is_linear = unsigned_det < linear_tolerance_det && dot(v10, v12) < 0.0;
        if (is_linear)
            return;

        bool too_steep;
        mat4 xyz_to_uv = get_xyz_to_uv(verts[0], verts[1], verts[2], 2.0, too_steep);

        is_convex = float(dot(curve_normal, vitem_unit_normal) > 0);

        for (int i = 0; i < 3; i++) {
            vec4 v4_vert = vec4(verts[i], 1.0);
            vec4 view_vert = view_matrix * v4_vert;
            vec4 proj_vert = proj_matrix * view_vert;

            gl_Position = wnd_matrix * proj_vert;
            gl_Position.z *= 0.1;

            uv_coords = (xyz_to_uv * v4_vert).xy;
            color = v_color[i];

            // 有无更好的方法计算 view_vert 到 proj_vert 的缩放系数？
            vec4 proj_vert_test = proj_matrix * (view_vert + vec4(1.0, 0.0, 0.0, 0.0));
            float proj_scale_factor = proj_vert_test.x / proj_vert_test.w - proj_vert.x / proj_vert.w;

            float scaled_aaw = anti_alias_width / proj_scale_factor;

            if (too_steep) {
                uv_anti_alias_width = scaled_aaw;
            } else {
                float f1 = length(xyz_to_uv[0].xyz);
                float f2 = length(xyz_to_uv[1].xyz);
                float f3 = length(xyz_to_uv[2].xyz);
                float uv_scale_factor = f1 + f2 + f3 - min(f1, min(f2, f3)) - max(f1, max(f2, f3));

                uv_anti_alias_width = scaled_aaw * uv_scale_factor;
            }

            EmitVertex();
        }
        EndPrimitive();

    } else {
        mat4 matrix = wnd_matrix * proj_matrix * view_matrix;
        for (int i = 0; i < 3; i++) {
            gl_Position = matrix * vec4(verts[i], 1.0);
            gl_Position.z *= 0.1;

            color = v_color[i];

            EmitVertex();
        }
        EndPrimitive();
    }
    
}
