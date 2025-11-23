
uniform samplerBuffer points;   // vec4(x, y, 0 or depth, 0)
                                // 在 vitem_plane 中 z 分量为 0，在 vitem_curve 中表示 depth

uniform samplerBuffer radii;    // radii[idx / 4][idx % 4]
uniform samplerBuffer colors;
uniform samplerBuffer fills;

vec2 get_point(int idx) {
    return texelFetch(points, idx).xy;
}

vec3 get_point_with_depth(int idx) {
    return texelFetch(points, idx).xyz;
}

float get_radius(int anchor_idx) {
    if (JA_FIX_IN_FRAME) {
        return texelFetch(radii, anchor_idx / 4)[anchor_idx % 4] * JA_CAMERA_SCALED_FACTOR;
    }
    return texelFetch(radii, anchor_idx / 4)[anchor_idx % 4];
}

vec4 get_color(int anchor_idx) {
    return texelFetch(colors, anchor_idx);
}

vec4 get_fill(int anchor_idx) {
    return texelFetch(fills, anchor_idx);
}
