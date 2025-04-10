
import os

import moderngl as mgl

from janim.render.base import Renderer, programs_map
from janim.render.uniform import apply_uniforms
from janim.utils.file_ops import find_file_or_none, get_janim_dir, readall

injection_ja_finish_up = '''if (!JA_BLENDING) {
        vec2 coord = gl_FragCoord.xy / vec2(textureSize(JA_FRAMEBUFFER, 0));
        vec4 back = texture(JA_FRAMEBUFFER, coord);
        float a = f_color.a + back.a * (1 - f_color.a);
        f_color = clamp(
            vec4(
                (f_color.rgb * f_color.a + back.rgb * back.a * (1 - f_color.a)) / a,
                a
            ),
            0.0, 1.0
        );
    }
'''

shader_injection = {
    'fragment_shader': [
        ('#[JA_FINISH_UP]', injection_ja_finish_up)
    ]
}


def inject_shader(shader_type: str, shader: str) -> str:
    injection = shader_injection.get(shader_type, None)
    if injection is None:
        return shader

    for key, content in injection:
        shader = shader.replace(key, content)
    return shader


shader_keys = (
    ('vertex_shader', '.vert.glsl'),
    ('geometry_shader', '.geom.glsl'),
    ('fragment_shader', '.frag.glsl')
)


def get_janim_program(filepath: str) -> mgl.Program:
    '''
    给定相对于 janim 路径的文件位置，自动遍历后缀并读取着色器代码，
    例如传入 ``render/shaders/dotcloud`` 后，会自动读取以下位置的代码：

    - redner/shaders/dotcloud.vert.glsl
    - render/shaders/dotcloud.geom.glsl
    - render/shaders/dotcloud.frag.glsl

    若没有则缺省，但要能创建可用的着色器

    注：

    - 若 ``filepath`` 对应着色器程序先前已创建过，则会复用先前的对象，否则另外创建新的对象并记录
    - 该方法只能读取 janim 内置的着色器，读取自定义着色器请使用 :meth:`get_custom_program`
    '''
    ctx = Renderer.data_ctx.get().ctx
    programs = programs_map[ctx]

    prog = programs.cache.get(filepath, None)
    if prog is not None:
        return prog

    shader_path = os.path.join(get_janim_dir(), filepath)

    # 这里不使用 get_program_from_string，是为了避免在有缓存时仍然读取一遍文件
    prog = ctx.program(**{
        shader_type: inject_shader(shader_type, readall(shader_path + suffix))
        for shader_type, suffix in shader_keys
        if os.path.exists(shader_path + suffix)
    })
    apply_uniforms(prog)

    programs.cache[filepath] = prog
    return prog


def get_custom_program(filepath: str) -> mgl.Program:
    '''
    给定文件位置自动遍历后缀并读取着色器代码，
    例如传入 ``shaders/yourshader`` 后，会自动读取以下位置的代码：

    - shaders/yourshader.vert.glsl
    - shaders/yourshader.geom.glsl
    - shaders/yourshader.frag.glsl

    若没有则缺省，但要能创建可用的着色器

    注：

    - 若 ``filepath`` 对应着色器程序先前已创建过，则会复用先前的对象，否则另外创建新的对象并记录
    - 该方法只能读取自定义的着色器，读取 janim 内置着色器请使用 :meth:`get_janim_program`
    '''
    ctx = Renderer.data_ctx.get().ctx
    programs = programs_map[ctx]

    prog = programs.cache.get(filepath, None)
    if prog is not None:
        return prog

    # 这里不使用 get_program_from_string，是为了避免在有缓存时仍然读取一遍文件
    prog = ctx.program(**{
        shader_type: inject_shader(shader_type, readall(_shader_path))
        for shader_type, suffix in shader_keys
        if (_shader_path := find_file_or_none(filepath + suffix)) is not None
    })
    apply_uniforms(prog)

    programs.cache[filepath] = prog
    return prog


def get_program_from_string(
    vertex_shader: str,
    fragment_shader: str | None = None,
    geometry_shader: str | None = None,
    *,
    cache_key: str | None = None
) -> mgl.Program:
    '''
    从着色器字符串创建着色器程序
    '''
    ctx = Renderer.data_ctx.get().ctx

    programs = programs_map[ctx]
    if cache_key is not None:
        prog = programs.cache.get(cache_key, None)
        if prog is not None:
            return prog

    prog = ctx.program(
        vertex_shader=inject_shader('vertex_shader', vertex_shader),
        fragment_shader=None if fragment_shader is None else inject_shader('fragment_shader', fragment_shader),
        geometry_shader=None if geometry_shader is None else inject_shader('geometry_shader', geometry_shader)
    )
    apply_uniforms(prog)

    if cache_key is not None:
        programs.cache[cache_key] = prog
    else:
        programs.additional.append(prog)

    return prog


def get_janim_compute_shader(filepath: str) -> mgl.ComputeShader:
    '''
    载入相对于 janim 目录的指定文件的 ComputeShader，
    例如 ``render/shaders/map_points.comp.glsl`` 就会载入 janim 文件夹中的这个文件

    注：若 ``filepath`` 对应的 ComputeShader 先前已创建过，则会复用先前的对象，否则另外创建新的对象并记录
    '''
    ctx = Renderer.data_ctx.get().ctx
    programs = programs_map[ctx]
    comp = programs.cache.get(filepath, None)
    if comp is not None:
        return comp

    shader_path = os.path.join(get_janim_dir(), filepath)

    comp = ctx.compute_shader(readall(shader_path))
    apply_uniforms(comp)

    programs.cache[filepath] = comp
    return comp
