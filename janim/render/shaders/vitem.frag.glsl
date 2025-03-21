#version 430 core

in vec2 v_coord;

out vec4 f_color;

uniform float JA_CAMERA_SCALED_FACTOR;
uniform float JA_ANTI_ALIAS_RADIUS;
uniform bool JA_FIX_IN_FRAME;

uniform bool stroke_background;
uniform bool is_fill_transparent;
uniform vec4 glow_color;
uniform float glow_size;

const float INFINITY = uintBitsToFloat(0x7F800000);

// used by JA_FINISH_UP
uniform bool JA_BLENDING;
uniform sampler2D JA_FRAMEBUFFER;

layout(std140, binding = 0) buffer MappedPoints
{
    vec4 points[];  // vec4(x, y, isclosed, 0)
};
layout(std140, binding = 1) buffer Radii
{
    vec4 radii[];   // radii[idx / 4][idx % 4]
};
layout(std140, binding = 2) buffer Colors
{
    vec4 colors[];
};
layout(std140, binding = 3) buffer Fills
{
    vec4 fills[];
};

vec2 get_point(int idx) {
    return points[idx].xy;
}

bool get_isclosed(int idx) {
    return bool(points[idx].z);
}

float get_radius(int idx) {
    if (JA_FIX_IN_FRAME) {
        return radii[idx / 4][idx % 4] * JA_CAMERA_SCALED_FACTOR;
    }
    return radii[idx / 4][idx % 4];
}

vec4 blend_color(vec4 fore, vec4 back) {
    float a = fore.a + back.a * (1 - fore.a);
    return clamp(
        vec4(
            (fore.rgb * fore.a + back.rgb * back.a * (1 - fore.a)) / a,
            a
        ),
        0.0, 1.0
    );
}

float cross2d(vec2 a, vec2 b) {
    return a.x * b.y - a.y * b.x;
}

float sign_bezier(vec2 A, vec2 B, vec2 C, vec2 p)
{
    vec2 a = C - A, b = B - A, c = p - A;
    vec2 bary = vec2(
        c.x * b.y - b.x * c.y,
        a.x * c.y - c.x * a.y
    ) / (a.x * b.y - b.x * a.y);
    vec2 d = vec2(bary.y * 0.5, 0.0) + 1.0 - bary.x - bary.y;

    float sign_bezierInside = d.x > d.y ? sign(d.x * d.x - d.y) : 1.0;

    bvec3 cond = bvec3( p.y >= A.y,
                        p.y <  C.y,
                        a.x * c.y > a.y * c.x );
    float signLineLeft = all(cond) || all(not(cond)) ? -1.0 : 1.0;

    return sign_bezierInside * signLineLeft;
}

vec3 solve_cubic(float a, float b, float c)
{
    float p = b - a * a / 3.0, p3 = p * p * p;
    float q = a * (2.0 * a * a - 9.0 * b) / 27.0 + c;
    float d = q * q + 4.0 * p3 / 27.0;
    float offset = -a / 3.0;
    if(d >= 0.0) {
        float z = sqrt(d);
        vec2 x = (vec2(z, -z) - q) / 2.0;
        vec2 uv = sign(x) * pow(abs(x), vec2(1.0 / 3.0));
        return vec3(offset + uv.x + uv.y);
    }
    float v = acos(-sqrt(-27.0 / p3) * q / 2.0) / 3.0;
    float m = cos(v), n = sin(v) * 1.732050808;
    return vec3(m + m, -n - m, n - m) * sqrt(-p / 3.0) + offset;
}

float distance_bezier(vec2 A, vec2 B, vec2 C, vec2 p)
{
    B = mix(B + vec2(1e-4), B, abs(sign(B * 2.0 - A - C)));
    vec2 a = B - A, b = A - B * 2.0 + C, c = a * 2.0, d = A - p;
    vec3 k = vec3(3. * dot(a, b),2. * dot(a, a) + dot(d, b),dot(d, a)) / dot(b, b);
    vec3 t = clamp(solve_cubic(k.x, k.y, k.z), 0.0, 1.0);
    vec2 pos = A + (c + b * t.x) * t.x;
    float dis = length(pos - p);
    pos = A + (c + b * t.y) * t.y;
    dis = min(dis, length(pos - p));
    pos = A + (c + b * t.z) * t.z;
    dis = min(dis, length(pos - p));
    return dis;
}

void get_subpath_attr(
    int start_idx,
    out int end_idx,
    out int idx,
    out float d,
    out float sgn
) {
    const int lim = (points.length() - 1) / 2 * 2;
    end_idx = lim;
    bool is_closed = get_isclosed(start_idx);

    d = INFINITY;
    sgn = 1.0;
    for (int i = start_idx; i < lim; i += 2) {
        vec2 B = get_point(i + 1);
        if (isnan(B.x)) {
            end_idx = i;
            break;
        }
        vec2 A = get_point(i), C = get_point(i + 2);
        if (A == B && B == C)
            continue;

        vec2 v1 = normalize(B - A);
        vec2 v2 = normalize(C - B);
        // REFACTOR: 使用更好的判断可近似为直线的方法
        if (abs(cross2d(v1, v2)) < 1e-3 && dot(v1, v2) > 0.0) {
            vec2 e = C - A;
            vec2 w = v_coord - A;
            vec2 b = w - e * clamp(dot(w, e) / dot(e, e), 0.0, 1.0);
            float dist = length(b);
            if (dist < d) {
                d = dist;
                idx = i;
            }

            if (is_closed) {
                bvec3 cond = bvec3( v_coord.y >= A.y,
                                    v_coord.y  < C.y,
                                    e.x * w.y > e.y * w.x );
                if(all(cond) || all(not(cond))) sgn = -sgn;
            }
        } else {
            float dist = distance_bezier(A, B, C, v_coord);
            if (dist < d) {
                d = dist;
                idx = i;
            }

            if (is_closed) {
                sgn *= sign_bezier(A, B, C, v_coord);
            }
        }
    }
}

// #define CONTROL_POINTS
// #define POLYGON_LINES
// #define SDF_PLANE

void main()
{
    float d;

    #ifdef CONTROL_POINTS

    d = distance(v_coord, get_point(0));
    for (int i = 1; i < points.length(); i++) {
        d = min(d, distance(v_coord, get_point(i)));
    }
    if (d < 0.06) {
        f_color = vec4(1.0 - smoothstep(0.048, 0.052, d));
        return;
    }

    #endif

    int idx;
    d = INFINITY;
    float sgn = 1.0;

    int start_idx = 0;
    float sp_d;
    float sp_sgn;

    const int lim = (points.length() - 1) / 2 * 2;

    while (true) {
        get_subpath_attr(start_idx, start_idx, idx, sp_d, sp_sgn);
        d = min(d, sp_d);
        sgn *= sp_sgn;

        if (start_idx >= lim)
            break;
        start_idx += 2;
    }
    int anchor_idx = idx / 2;
    float sgn_d = sgn * d;

    vec2 e = get_point(idx + 2) - get_point(idx);
    vec2 w = v_coord - get_point(idx);
    float ratio = clamp(dot(w, e) / dot(e, e), 0.0, 1.0);

    float radius = mix(get_radius(anchor_idx), get_radius(anchor_idx + 1), ratio);

    vec4 fill_color = get_isclosed(idx) ? mix(fills[anchor_idx], fills[anchor_idx + 1], ratio) : vec4(0.0);
    fill_color.a *= smoothstep(1, -1, (sgn_d) / JA_ANTI_ALIAS_RADIUS);

    vec4 stroke_color = mix(colors[anchor_idx], colors[anchor_idx + 1], ratio);
    stroke_color.a *= smoothstep(1, -1, (d - radius) / JA_ANTI_ALIAS_RADIUS);

    if (stroke_background) {
        f_color = blend_color(fill_color, stroke_color);
    } else {
        f_color = blend_color(stroke_color, fill_color);
    }

    if (glow_color.a != 0.0) {
        float factor;
        if (is_fill_transparent) {
            factor = 1.0 - d / glow_size;
        } else {
            factor = 1.0 - sgn_d / glow_size;
        }
        if (0.0 < factor && factor <= 1.0) {
            vec4 f_glow_color = glow_color;
            f_glow_color.a *= factor * factor;
            f_color = blend_color(f_color, f_glow_color);
        }
    }

    #if !defined(POLYGON_LINES) && !defined(SDF_PLANE)
    if (f_color.a == 0.0)
        discard;
    #endif

    #ifdef SDF_PLANE

    vec4 df_color = vec4(1.0) - sgn * vec4(0.1, 0.4, 0.7, 0.0);
    df_color *= 0.8 + 0.2 * cos(140. * d / 3.0);
    df_color = mix(df_color, vec4(1.0), 1.0 - smoothstep(0.0, 0.02, abs(d)));
    df_color.a = 0.5;
    f_color = blend_color(df_color, f_color);

    #endif

    #ifdef POLYGON_LINES

    const int num = points.length();
    d = dot(v_coord - get_point(0), v_coord - get_point(0));
    for(int i = 1, j = 0; i < num; j = i, i++)
    {
        if (get_point(j) == get_point(i)) {
            i++;
            continue;
        }
        // distance
        vec2 e = get_point(j) - get_point(i);
        vec2 w = v_coord - get_point(i);
        vec2 b = w - e * clamp(dot(w, e) / dot(e, e), 0.0, 1.0);
        d = min(d, dot(b, b));
    }
    float line_ratio = smoothstep(1.15, 0.85, sqrt(d) / 0.02);
    f_color.g = max(line_ratio, f_color.g);
    f_color.a = max(line_ratio, f_color.a);

    #endif

    #[JA_FINISH_UP]
}