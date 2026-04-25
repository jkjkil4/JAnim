
#include "JA_CAMERA_LOC.glsl"
uniform vec3 JA_LIGHT_SOURCE;

const float REFLECTIVENESS = 0.3;
const float GLOSS = 0.2;
const float SHADOW = 0.4;

// borrowed from 3b1b/manim finalize_color.glsl
vec3 apply_light(vec3 color, vec3 point, vec3 unit_normal)
{
    vec3 to_camera = normalize(JA_CAMERA_LOC - point);
    vec3 to_light = normalize(JA_LIGHT_SOURCE - point);

    float light_to_normal = dot(to_light, unit_normal);
    // When unit normal points towards light, brighten
    float bright_factor = max(light_to_normal, 0.0) * REFLECTIVENESS;
    
    // For glossy surface, add extra shine if light beam goes towwards camera
    vec3 light_reflection = reflect(-to_light, unit_normal);
    float light_to_cam = dot(light_reflection, to_camera);
    float shine = GLOSS * exp(-3.0 * pow(1.0 - light_to_cam, 2));
    bright_factor += shine;

    vec3 result = mix(color, vec3(1.0), bright_factor);
    if (light_to_normal < 0.0) {
        // Darken
        result = mix(result, vec3(0.0), max(-light_to_normal, 0.0) * SHADOW);
    }
    return result;
}

