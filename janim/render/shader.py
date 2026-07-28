import re
from contextvars import ContextVar
from pathlib import Path

import moderngl as mgl

from janim.exception import ShaderInjectionNotFoundError
from janim.locale import get_translator
from janim.utils.file_ops import find_file, find_file_in_path, get_janim_dir, readall

_ = get_translator('janim.render.shader')

# region main part


def resolve_shader_from_file(file_path: str) -> str:
    """
    读取 ``file_path`` shader 文件，并解析其中的 “预编译宏”

    -   对于 ``#include "xxx"`` ，会读取对应的文件

        若某个文件存在重复包含的情况，则仅第一次有效，后续会直接忽略

    -   对于 ``#version xxx core`` ，会提取遇到的最高版本写到结果字符串的开头
    """
    found_path = find_shader_file(file_path)
    info = _ResolveInfo()
    _resolve_shader_from_file(found_path, info)
    info.lines.append('//')  # 避免可能出现在结尾的 #line 没有后续代码导致在部分平台上报错
    return (
        f'#version {info.max_version} core\n'  #
        + '\n'.join(info.lines)
    )


def resolve_shader_from_file_or_none(file_path: str) -> str | None:
    """
    和 :py:func:`resolve_shader_from_file` 一样，区别在于在找不到文件时返回 ``None``
    """
    try:
        found_path = find_shader_file(file_path)
    except FileNotFoundError:
        return None
    info = _ResolveInfo()
    _resolve_shader_from_file(found_path, info)
    info.lines.append('//')  # 避免可能出现在结尾的 #line 没有后续代码导致在部分平台上报错
    return (
        f'#version {info.max_version} core\n'  #
        + '\n'.join(info.lines)
    )


def resolve_shader_from_source(name: str, source: str, dir_path: str | None = None) -> str:
    """
    处理 ``source`` 代码，解析其中的 “预编译宏”

    -   对于 ``#include "xxx"`` ，会读取对应的文件

        若某个文件存在重复包含的情况，则仅第一次有效，后续会直接忽略

        ``dir_path`` 决定了其搜索基于的路径

    -   对于 ``#version xxx core`` ，会提取遇到的最高版本写到结果字符串的开头
    """
    info = _ResolveInfo()
    _resolve_shader_from_source(name, source, info, dir_path)
    return (
        f'#version {info.max_version} core\n'  #
        + '\n'.join(info.lines)
    )


class _ResolveInfo:
    def __init__(self):
        self.lines: list[str] = []
        self.max_version: int = 330

        self.resolved_files: set[Path] = set()


_regex_version = re.compile(r'^\s*#\s*version\s+(\d+)\s+core\s*$')
_regex_include = re.compile(r'^\s*#\s*include\s+"([^"]+)"\s*$')
_regex_injection = re.compile(r'^\s*#\[\s*([^\]]+)\s*\]\s*$')


def _resolve_shader_from_file(file_path: str, info: _ResolveInfo) -> None:
    path = Path(file_path).resolve()

    # 尝试寻找合适的 rel_path 简化插入 glsl "#line" 对应的路径
    rel_path = path
    try:
        rel_path = path.relative_to(get_janim_dir())
    except ValueError:
        try:
            rel_path = path.relative_to(Path.cwd())
        except ValueError:
            pass
    rel_path_str = repr(str(rel_path))

    # 避免重复包含
    if path in info.resolved_files:
        return
    info.resolved_files.add(path)
    _resolve_shader_from_source(rel_path_str, readall(file_path), info, str(path.parent))


def _resolve_shader_from_source(
    name: str, source: str, info: _ResolveInfo, dir_path: str | None
) -> None:
    nameidx = name_to_idx(name)
    info.lines.append(f'#line 1 {nameidx}')

    for i, line in enumerate(source.splitlines(), start=1):
        # 匹配例如 #version 330 core，提取最大需求版本
        match = _regex_version.match(line)
        if match:
            info.max_version = max(info.max_version, int(match.group(1)))
            info.lines.append('')
            continue

        # 匹配例如 #include "xxx"
        match = _regex_include.match(line)
        if match:
            included_file = match.group(1)
            # 递归读取包含的文件
            found_file = find_shader_file(included_file, dir_path)
            _resolve_shader_from_file(found_file, info)
            # 返回原先的文件，需要恢复行号
            info.lines.append(f'#line {i + 1} {nameidx}')
            continue

        # 匹配例如 #[xxx]
        match = _regex_injection.match(line)
        if match:
            # 插入 injection
            _resolve_shader_injection(match.group(1), info)
            # 返回原先的文件，需要恢复行号
            info.lines.append(f'#line {i + 1} {nameidx}')
            continue

        # 没有匹配到以上任意项，则保留该行原始内容
        info.lines.append(line)


# endregion

# region name index conversion


_shader_nameidx_mapping: dict[str, int] = {}


def name_to_idx(name: str) -> int:
    idx = _shader_nameidx_mapping.get(name, None)
    if idx is None:
        idx = len(_shader_nameidx_mapping) + 1
        _shader_nameidx_mapping[name] = idx
    return idx


def idx_to_name(idx: int) -> str | None:
    for name, i in _shader_nameidx_mapping.items():
        if i == idx:
            return name
    return None


def convert_error_nameidx_to_name(error: mgl.Error) -> None:
    """
    将 ModernGL 报错信息中的 nameidx 转换为 name
    """
    if len(error.args) != 1:
        return

    msg: str = error.args[0]

    def replace_line(line: str) -> str:
        for regex in [
            r'^(\d+)\(\d+\) : .*$',  # Windows?
            r'^.*?: (\d+):\d+: .*$',  # macOS?
            r'^(\d+):\d+\(\d+\): .*$',  # Linux?
        ]:
            match = re.match(regex, line)
            if not match:
                continue
            nameidx = int(match.group(1))
            start, end = match.span(1)
            name = idx_to_name(nameidx)
            if name is None:
                return line
            return line[:start] + name + line[end:]

        return line

    lines = [replace_line(line) for line in msg.splitlines()]

    error.args = ('\n'.join(lines),)


# endregion

# region utils


def find_shader_file(file_path: str, dir_path: str | None = None) -> str:
    # 优先在 dir_path 中查找
    if dir_path is not None:
        found_path = find_file_in_path(dir_path, file_path)
        if found_path is not None:
            return found_path

    # 其次在 janim 目录中查找
    found_path = find_file_in_path(get_janim_dir(), file_path)
    if found_path is not None:
        return found_path

    # 最后用 find_file 查找
    return find_file(file_path)


# endregion

# region shader injection

# PMA，即预乘透明度混合方案
_injection_ja_finish_up = '    f_color.rgb *= f_color.a;'

# 仅用于前向兼容
_injection_ja_finish_up_uniforms = ''

shader_injections_ctx: ContextVar[list[dict[str, str]]] = ContextVar('shader_injections_ctx')
shader_injections_ctx.set(
    [
        {
            'JA_FINISH_UP': _injection_ja_finish_up,
            'JA_FINISH_UP_UNIFORMS': _injection_ja_finish_up_uniforms,
        }
    ]
)


class ShaderInjection:
    def __init__(self, **kwargs):
        self.injection = kwargs
        self.token = None

    def __enter__(self):
        lst = shader_injections_ctx.get()
        self.token = shader_injections_ctx.set([*lst, self.injection])
        return self

    def __exit__(self, exc_type, exc_value, tb):
        shader_injections_ctx.reset(self.token)

    @staticmethod
    def find(name: str) -> str:
        for injection in reversed(shader_injections_ctx.get()):
            if name in injection:
                return injection[name]
        raise ShaderInjectionNotFoundError(_('ShaderInjection not found: {name}').format(name=name))


def _resolve_shader_injection(name: str, info: _ResolveInfo) -> None:
    nameidx = name_to_idx(name)
    info.lines.append(f'#line 1 {nameidx}')
    info.lines.extend(ShaderInjection.find(name).splitlines())


# endregion
