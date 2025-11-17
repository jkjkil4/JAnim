
float cross2d(vec2 a, vec2 b) {
    return a.x * b.y - a.y * b.x;
}

bool is_approx_line(vec2 A, vec2 B, vec2 C) {
    vec2 v1 = normalize(B - A);
    vec2 v2 = normalize(C - B);
    // REFACTOR: 使用更好的判断可近似为直线的方法
    return abs(cross2d(v1, v2)) < 1e-3 && dot(v1, v2) > 0.0;
}
