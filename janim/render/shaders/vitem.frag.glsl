#version 430 core

in vec2 v_coord;

out vec4 f_color;

uniform float JA_ANTI_ALIAS_RADIUS;

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
    return radii[idx / 4][idx % 4];
}

vec4 blendColor(vec4 fore, vec4 back) {
    float a = fore.a + back.a * (1 - fore.a);
    return vec4(
        (fore.rgb * fore.a + back.rgb * back.a * (1 - fore.a)) / a,
        a
    );
}

float signBezier(vec2 A, vec2 B, vec2 C, vec2 p)
{
    vec2 a = C - A, b = B - A, c = p - A;
    vec2 bary = vec2(
        c.x * b.y - b.x * c.y,
        a.x * c.y - c.x * a.y
    ) / (a.x * b.y - b.x * a.y);
    vec2 d = vec2(bary.y * 0.5, 0.0) + 1.0 - bary.x - bary.y;

    float signBezierInside = d.x > d.y ? sign(d.x * d.x - d.y) : 1.0;

    bvec3 cond = bvec3( p.y >= A.y,
                        p.y <  C.y,
                        a.x * c.y > a.y * c.x );
    float signLineLeft = all(cond) || all(not(cond)) ? -1.0 : 1.0;

    return signBezierInside * signLineLeft;
}

vec3 solveCubic(float a, float b, float c)
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

float distanceBezier(vec2 A, vec2 B, vec2 C, vec2 p)
{
    B = mix(B + vec2(1e-4), B, abs(sign(B * 2.0 - A - C)));
    vec2 a = B - A, b = A - B * 2.0 + C, c = a * 2.0, d = A - p;
    vec3 k = vec3(3. * dot(a, b),2. * dot(a, a) + dot(d, b),dot(d, a)) / dot(b, b);
    vec3 t = clamp(solveCubic(k.x, k.y, k.z), 0.0, 1.0);
    vec2 pos = A + (c + b * t.x) * t.x;
    float dis = length(pos - p);
    pos = A + (c + b * t.y) * t.y;
    dis = min(dis, length(pos - p));
    pos = A + (c + b * t.z) * t.z;
    dis = min(dis, length(pos - p));
    return dis;
}

// #define CONTROL_POINTS

void main()
{
    float d;

    #ifdef CONTROL_POINTS

    d = distance(v_coord, get_point(0));
    for (int i = 1; i < points.length(); i++) {
        d = min(d, distance(v_coord, get_point(i)));
    }
    if (d < 0.04 * 2) {
        f_color = vec4(1.0 - smoothstep(0.025 * 2, 0.034 * 2, d));
        return;
    }

    #endif

    // Get the signed distance to bezier curve
    d = distanceBezier(get_point(0), get_point(1), get_point(2), v_coord);
    float sgn = (
        get_isclosed(0)
        ? signBezier(get_point(0), get_point(1), get_point(2), v_coord)
        : 1.0
    );
    int idx = 0;
    for (int i = 2; i < points.length() - 2; i += 2) {
        if (get_point(i) == get_point(i + 1))
            continue;
        float dist = distanceBezier(get_point(i), get_point(i + 1), get_point(i + 2), v_coord);
        if (dist < d) {
            d = dist;
            idx = i;
        }
        if (get_isclosed(i)) {
            sgn *= signBezier(get_point(i), get_point(i + 1), get_point(i + 2), v_coord);
        }
    }
    int anchor_idx = idx / 2;
    float sgn_d = sgn * d;

    //
    vec2 e = get_point(idx + 2) - get_point(idx);
    vec2 w = v_coord - get_point(idx);
    float ratio = clamp(dot(w, e) / dot(e, e), 0.0, 1.0);

    float radius = mix(get_radius(anchor_idx), get_radius(anchor_idx + 1), ratio);

    if (sgn > 0 && d > radius + JA_ANTI_ALIAS_RADIUS)
        discard;

    vec4 fill_color = vec4(0.0);
    if (get_isclosed(idx)) {
        fill_color = mix(fills[anchor_idx], fills[anchor_idx + 1], ratio);
        fill_color.a *= smoothstep(1, -1, (sgn_d) / JA_ANTI_ALIAS_RADIUS);
    }

    vec4 stroke_color = mix(colors[anchor_idx], colors[anchor_idx + 1], ratio);
    stroke_color.a *= smoothstep(1, -1, (d - radius) / JA_ANTI_ALIAS_RADIUS);

    f_color = blendColor(stroke_color, fill_color);
}