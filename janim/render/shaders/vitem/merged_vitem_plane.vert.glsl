#version 430 core

// Instanced vertex shader for merged GPU-driven VItem rendering.
// gl_InstanceID = item index
// gl_VertexID = 0..3 (quad corners)

uniform vec2 JA_FRAME_RADIUS;

layout(std430, binding = 5) buffer ClipBoxes {
    // 4 vec2 per item, stored as vec4 (xy pairs)
    vec4 clip_boxes[];  // clip_boxes[item*2 + 0] = (x0,y0, x1,y1), clip_boxes[item*2 + 1] = (x2,y2, x3,y3)
};

out vec2 v_coord;
flat out int v_item_idx;

void main()
{
    int item_idx = gl_InstanceID;
    v_item_idx = item_idx;

    // Read clip box for this item (4 corners stored as 2 vec4s)
    vec4 box0 = clip_boxes[item_idx * 2];
    vec4 box1 = clip_boxes[item_idx * 2 + 1];

    // corners: (box0.xy, box0.zw, box1.xy, box1.zw) in TRIANGLE_STRIP order
    vec2 coord;
    if (gl_VertexID == 0) coord = box0.xy;
    else if (gl_VertexID == 1) coord = box0.zw;
    else if (gl_VertexID == 2) coord = box1.xy;
    else coord = box1.zw;

    gl_Position = vec4(coord, 0.0, 1.0);
    v_coord = coord * JA_FRAME_RADIUS;
}
