float sign_line(vec2 A, vec2 C, vec2 p)
{
    vec2 e = C - A;
    vec2 w = p - A;
    bvec3 cond = bvec3( p.y >= A.y,
                        p.y  < C.y,
                        e.x * w.y > e.y * w.x );
    if(all(cond) || all(not(cond)))
        return -1.0;
    return 1.0;
}

float distance_line(vec2 A, vec2 C, vec2 p)
{
    vec2 e = C - A;
    vec2 w = p - A;
    vec2 b = w - e * clamp(dot(w, e) / dot(e, e), 0.0, 1.0);
    return length(b);
}