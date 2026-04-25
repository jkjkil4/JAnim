
uniform vec3 JA_LIGHT_SOURCE;

float get_shade(vec3 start_point, vec3 unit_normal)
{
    vec3 to_sun = normalize(JA_LIGHT_SOURCE - start_point);
    float dotv = dot(unit_normal, to_sun);
    float light = 0.5 * dotv * dotv * dotv;
    if (light < 0.0)
        light *= 0.5;
    return light;
}

