#version 430 core

layout(points) in;
layout(triangle_strip, max_vertices = 6) out;

in int v_prev_idx[1];
in int v_curr_idx[1];
in int v_next_idx[1];

out vec2 v_coord;

flat out int curr_idx;

uniform float JA_CAMERA_SCALED_FACTOR;
uniform vec2 JA_FRAME_RADIUS;
uniform float JA_ANTI_ALIAS_RADIUS;
uniform bool JA_FIX_IN_FRAME;

uniform vec4 glow_color;
uniform float glow_size;

#include "layouts/layout.glsl"

#include "vitem_curve_geom_main.glsl"
