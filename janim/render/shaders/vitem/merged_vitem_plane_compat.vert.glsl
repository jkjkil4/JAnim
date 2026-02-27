#version 330 core

// Instanced vertex shader for merged GPU-driven VItem rendering (GL 3.3).
// Uses instanced attributes for per-item clip box corners.

uniform vec2 JA_FRAME_RADIUS;

// Per-instance attributes: 4 clip box corners (2D each)
// Packed as 2 vec4: (x0,y0,x1,y1) and (x2,y2,x3,y3)
in vec4 in_clip_box0;  // (corner0.xy, corner1.xy)
in vec4 in_clip_box1;  // (corner2.xy, corner3.xy)

// Per-instance item index
in float in_item_idx;

out vec2 v_coord;
flat out int v_item_idx;

void main()
{
    v_item_idx = int(in_item_idx);

    // gl_VertexID selects which corner of the quad (TRIANGLE_STRIP: 0,1,2,3)
    vec2 coord;
    if (gl_VertexID == 0) coord = in_clip_box0.xy;
    else if (gl_VertexID == 1) coord = in_clip_box0.zw;
    else if (gl_VertexID == 2) coord = in_clip_box1.xy;
    else coord = in_clip_box1.zw;

    gl_Position = vec4(coord, 0.0, 1.0);
    v_coord = coord * JA_FRAME_RADIUS;
}
