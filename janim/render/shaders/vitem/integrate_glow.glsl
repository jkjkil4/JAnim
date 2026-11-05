// 该函数由 LLM 编写，未 review
// 主要向 LLM 提及了参数约定和线元光强的衰减系数：max(0.0, dist / glow_size) ^ 2
float integrate_glow(vec2 A, vec2 B, float dalpha) {
    vec2 D = B - A;
    vec2 U = A - v_coord;

    float L = length(D);
    float r = glow_size;

    if (L < 1e-7 || r <= 0.0) {
        return 0.0;
    }

    vec2 dir = D / L;

    // 投影位置与垂直距离
    float s0 = -dot(U, dir);
    float h2 = max(0.0, dot(U, U) - s0 * s0);

    // 光强为正的区域
    float q2 = r * r - h2;

    if (q2 <= 0.0) {
        return 0.0;
    }

    float q = sqrt(q2);

    // 裁剪积分区间
    float x0 = max(-s0, -q);
    float x1 = min(L - s0, q);

    if (x0 >= x1) {
        return 0.0;
    }

    float integral;

    if (h2 < 1e-4) {
        // h -> 0 的极限形式，避免 log(0)
        float F0 = x0
                 + x0 * x0 * x0 / (3.0 * r * r)
                 - x0 * abs(x0) / r;

        float F1 = x1
                 + x1 * x1 * x1 / (3.0 * r * r)
                 - x1 * abs(x1) / r;

        integral = F1 - F0;
    } else {
        float h = sqrt(h2);

        float root0 = sqrt(x0 * x0 + h2);
        float root1 = sqrt(x1 * x1 + h2);

        float G0 = x0 * root0
                 + h2 * log(x0 + root0);

        float G1 = x1 * root1
                 + h2 * log(x1 + root1);

        float F0 = x0
                 + (x0 * x0 * x0 / 3.0 + h2 * x0)
                   / (r * r)
                 - G0 / r;

        float F1 = x1
                 + (x1 * x1 * x1 / 3.0 + h2 * x1)
                   / (r * r)
                 - G1 / r;

        integral = F1 - F0;
    }

    return dalpha * max(0.0, integral);
}

float integrate_bezier_glow(
    vec2 A,
    vec2 B,
    vec2 C,
    float dalpha
) {
    float result = 0.0;
    // 把曲线切成四段计算，效果已经足够
    const int N = 4;

    vec2 prev = A;

    for (int i = 1; i <= N; i++) {
        float t = float(i) / float(N);
        float s = 1.0 - t;

        vec2 P = s * s * A
               + 2.0 * s * t * B
               + t * t * C;

        result += integrate_glow(prev, P, dalpha);

        prev = P;
    }

    return result;
}

void integrate_curve_glow(
    vec2 A,
    vec2 B,
    vec2 C,
    inout float factor
) {
    if (A == B && B == C)
        return;
    factor += integrate_bezier_glow(A, B, C, 1 / glow_size);
}

void integrate_subpath_glow(
    int start_idx,
    int lim,
    out int end_idx,
    out float factor
) {
    end_idx = lim;

    factor = 0.0;

    for (int i = start_idx; i < lim; i += 2) {
        vec2 B = get_point(i + 1);
        if (isnan(B.x)) {
            end_idx = i;
            break;
        }
        vec2 A = get_point(i), C = get_point(i + 2);
        integrate_curve_glow(A, B, C, factor);
    }

    // 在 vitem-curve 中会设置这个，因为 vitem-curve 中没有 is_fill_transparent
    #ifndef INTEGRATE_GLOW_IN_VITEM_CURVE
    if (!is_fill_transparent) {
        vec2 A = get_point(end_idx);
        vec2 C = get_point(start_idx);
        vec2 B = (A + C) * 0.5;
        integrate_curve_glow(A, B, C, factor);
    }
    #endif
}

float get_glow_factor(int lim)
{
    float factor = 0.0;

    int start_idx = 0;
    float sp_factor;

    while (true) {
        integrate_subpath_glow(start_idx, lim, start_idx, sp_factor);
        #ifdef INTEGRATE_GLOW_IN_VITEM_CURVE
        factor += sp_factor;
        #else
        if (is_fill_transparent) {
            factor += sp_factor;
        } else {
            factor = max(factor, sp_factor);
        }
        #endif

        if (start_idx >= lim)
            break;
        start_idx += 2;
    }

    return min(1.0, factor);
}
