
import moderngl as mgl

from janim.render.base import Renderer, programs_map
from janim.render.shader import (convert_error_nameidx_to_name,
                                 preprocess_shader, read_shader,
                                 read_shader_or_none)
from janim.render.uniform import apply_uniforms

shader_keys = (
    ('vertex_shader', '.vert.glsl'),
    ('geometry_shader', '.geom.glsl'),
    ('fragment_shader', '.frag.glsl')
)


def get_program_from_file_prefix(filepath_prefix: str) -> mgl.Program:
    """
    给定相对于 janim 路径或用户路径的文件位置，自动遍历后缀并读取着色器代码，
    例如传入 ``render/shaders/dotcloud`` 后，会自动读取以下位置的代码：

    - ``render/shaders/dotcloud.vert.glsl``
    - ``render/shaders/dotcloud.geom.glsl``
    - ``render/shaders/dotcloud.frag.glsl``

    若没有则缺省，但要能创建可用的着色器

    注：若 ``filepath`` 对应着色器程序先前已创建过，则会复用先前的对象，否则另外创建新的对象并记录
    """
    ctx = Renderer.data_ctx.get().ctx
    programs = programs_map[ctx]

    prog = programs.cache.get(filepath_prefix, None)
    if prog is not None:
        return prog

    try:
        prog = ctx.program(**{
            shader_type: shader_code
            for shader_type, suffix in shader_keys
            if (shader_code := read_shader_or_none(filepath_prefix + suffix)) is not None
        })
    except mgl.Error as e:
        convert_error_nameidx_to_name(e)
        raise
    apply_uniforms(prog)

    programs.cache[filepath_prefix] = prog
    return prog


def get_program_from_files(
    vertex_shader_file: str,
    fragment_shader_file: str | None = None,
    geometry_shader_file: str | None = None,
) -> mgl.Program:
    """
    具体给定文件路径，读取着色器代码

    注：若对应的着色器程序先前已创建过，则会复用先前的对象，否则另外创建新的对象并记录
    """
    ctx = Renderer.data_ctx.get().ctx
    programs = programs_map[ctx]

    key = {'v': vertex_shader_file, 'f': fragment_shader_file, 'g': geometry_shader_file}

    prog = programs.cache.get(key, None)
    if prog is not None:
        return prog

    try:
        prog = ctx.program(
            vertex_shader=read_shader(vertex_shader_file),
            fragment_shader=None if fragment_shader_file is None else read_shader(fragment_shader_file),
            geometry_shader=None if geometry_shader_file is None else read_shader(geometry_shader_file)
        )
    except mgl.Error as e:
        convert_error_nameidx_to_name(e)
        raise
    apply_uniforms(prog)

    programs.cache[key] = prog
    return prog


def get_program_from_string(
    vertex_shader: str,
    fragment_shader: str | None = None,
    geometry_shader: str | None = None,
    *,
    cache_key: str | None = None,
    shader_name: str = ''
) -> mgl.Program:
    """
    从着色器字符串创建着色器程序

    注：可以指定 ``cache_key`` 提供缓存，若先前创建过 ``cache_key`` 对应的着色器程序，则会复用先前的对象
    """
    ctx = Renderer.data_ctx.get().ctx

    programs = programs_map[ctx]
    if cache_key is not None:
        prog = programs.cache.get(cache_key, None)
        if prog is not None:
            return prog

    try:
        prog = ctx.program(
            vertex_shader=preprocess_shader(shader_name, vertex_shader),
            fragment_shader=None if fragment_shader is None else preprocess_shader(shader_name, fragment_shader),
            geometry_shader=None if geometry_shader is None else preprocess_shader(shader_name, geometry_shader)
        )
    except mgl.Error as e:
        convert_error_nameidx_to_name(e)
        raise
    apply_uniforms(prog)

    if cache_key is not None:
        programs.cache[cache_key] = prog
    else:
        programs.additional.append(prog)

    return prog


def get_compute_shader_from_file(filepath: str) -> mgl.ComputeShader:
    """
    载入相对于 janim 路径或用户路径的 ``ComputeShader``，
    例如 ``render/shaders/map_points.comp.glsl`` 就会载入 janim 文件夹中的这个文件

    注：若 ``filepath`` 对应的 ``ComputeShader`` 先前已创建过，则会复用先前的对象，否则另外创建新的对象并记录
    """
    ctx = Renderer.data_ctx.get().ctx
    programs = programs_map[ctx]
    comp = programs.cache.get(filepath, None)
    if comp is not None:
        return comp

    comp = ctx.compute_shader(read_shader(filepath))
    apply_uniforms(comp)

    programs.cache[filepath] = comp
    return comp
