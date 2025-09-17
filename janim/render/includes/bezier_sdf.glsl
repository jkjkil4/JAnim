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