#version 330 core

in ivec3 in_indices;

out int v_idx;
out int v_prev_idx;
out int v_next_idx;

void main()
{
    v_idx = in_indices.x;
    v_prev_idx = in_indices.y;
    v_next_idx = in_indices.z;
}
