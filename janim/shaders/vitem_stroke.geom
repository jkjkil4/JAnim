#version 330 core
layout (triangles) in;
layout (triangle_strip, max_vertices = 6) out;

in vec4 verts[3];
in vec4 v_color[3];
in float v_stroke_width[3];

out vec2 pos[3];
out vec2 uv_coords;
out vec4 color;
out float uv_stroke_width;
out float uv_anti_alias_width;
out float is_linear;

uniform float anti_alias_width;
uniform mat4 proj_matrix;
uniform mat4 wnd_matrix;

const float tolerance_det = 0.01;

float cross2d(vec2 v, vec2 w)
{
    return v.x * w.y - w.x * v.y;
}

vec4 normalize_w(vec4 vect) 
{
    return vect / vect.w;
}

vec2 find_intersection(vec2 p0, vec2 v0, vec2 p1, vec2 v1)
{
    // Find the intersection of a line passing through
    // p0 in the direction v0 and one passing through p1 in
    // the direction p1.
    // That is, find a solutoin to p0 + v0 * t = p1 + v1 * s
    float det = -v0.x * v1.y + v1.x * v0.y;
    float t = cross2d(p0 - p1, v1) / det;
    return p0 + v0 * t;
}

vec2 xs_on_clean_parabola(vec3 b0, vec3 b1, vec3 b2){
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


mat4 map_triangles(vec3 src0, vec3 src1, vec3 src2, vec3 dst0, vec3 dst1, vec3 dst2){
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


mat4 rotation(vec3 axis, float cos_angle){
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


mat4 map_onto_x_axis(vec3 src0, vec3 src1){
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
){
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
    
    vec4 proj_pos[3];
    for (int i = 0; i < 3; i++) {
        proj_pos[i] = normalize_w(verts[i]);
        pos[i] = proj_pos[i].xy;
    }

    vec2 v10 = proj_pos[0].xy - proj_pos[1].xy;
    vec2 v12 = proj_pos[2].xy - proj_pos[1].xy;
    vec4 v10_perp = vec4(v_stroke_width[0] * 0.5 * normalize(vec2(-v10.y, v10.x)), 0.0, 0.0);
    vec4 v12_perp = vec4(v_stroke_width[2] * 0.5 * normalize(vec2(-v12.y, v12.x)), 0.0, 0.0);

    vec4 vert[6];
    float det = cross2d(normalize(v10), normalize(v12));
    is_linear = float(abs(det) < tolerance_det && dot(v10, v12) < 0.0);
    if (bool(is_linear)) {
        /*
            0---2---4
            |       |
            1---3---5
        */
        vert[0] = proj_pos[0] - v10_perp;
        vert[1] = proj_pos[0] + v10_perp;
        vert[4] = proj_pos[2] + v12_perp;
        vert[5] = proj_pos[2] - v12_perp;

        vert[2] = (vert[0] + vert[4]) / 2.0;
        vert[3] = (vert[1] + vert[5]) / 2.0;
    } else {
        if (det > 0.0) {  // right-turn
            /*
                2--------4
                |        |
                |        5
                |     3
                0---1
            */
            vert[0] = proj_pos[0] - v10_perp;
            vert[1] = proj_pos[0] + v10_perp;
            vert[4] = proj_pos[2] + v12_perp;
            vert[5] = proj_pos[2] - v12_perp;

            vert[2] = vec4(find_intersection(vert[0].xy, v10, vert[4].xy, v12), proj_pos[1].z, 1.0);
            vert[3] = (vert[1] + vert[5]) / 2;
        } else {        // left-turn
            /*
                4--------2
                |        |
                5        |
                   3     |
                     1---0
            */
            vert[0] = proj_pos[0] + v10_perp;
            vert[1] = proj_pos[0] - v10_perp;
            vert[4] = proj_pos[2] - v12_perp;
            vert[5] = proj_pos[2] + v12_perp;

            vert[2] = vec4(find_intersection(vert[0].xy, v10, vert[4].xy, v12), proj_pos[1].z, 1.0);
            vert[3] = (vert[1] + vert[5]) / 2.0;
        }
    }

    bool too_steep;
    mat4 xyz_to_uv;
    float uv_scale_factor;
    if (!bool(is_linear)) {
        xyz_to_uv = get_xyz_to_uv(proj_pos[0].xyz, proj_pos[1].xyz, proj_pos[2].xyz, 2.0, too_steep);
        is_linear = float(too_steep);
        uv_scale_factor = length(xyz_to_uv[0].xyz);
    }

    for (int i = 0; i < 6; i++) {
        gl_Position = wnd_matrix * proj_matrix * vert[i];
        float stroke_width = v_stroke_width[i / 2];

        if (bool(is_linear)) {
            float sgn = vec2(-1, 1)[i % 2];
            uv_coords = vec2(0, sgn * (0.5 * stroke_width));
            color = v_color[i / 2];
            uv_stroke_width = stroke_width;
            uv_anti_alias_width = anti_alias_width;
        } else {
            uv_coords = (xyz_to_uv * vert[i]).xy;
            color = v_color[i / 2];
            uv_stroke_width = stroke_width * uv_scale_factor;
            uv_anti_alias_width = anti_alias_width * uv_scale_factor;
        }
        EmitVertex();
    }
    EndPrimitive();
}
