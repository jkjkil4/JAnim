#ifndef _BLEND_COLOR_GLSL_
#define _BLEND_COLOR_GLSL_

vec4 blend_color(vec4 fore, vec4 back) {
    float a = fore.a + back.a * (1 - fore.a);
    return clamp(
        vec4(
            (fore.rgb * fore.a + back.rgb * back.a * (1 - fore.a)) / a,
            a
        ),
        0.0, 1.0
    );
}

#endif