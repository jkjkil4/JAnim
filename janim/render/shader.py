import re
from contextvars import ContextVar
from pathlib import Path

from janim.exception import ShaderInjectionNotFoundError
from janim.locale.i18n import get_local_strings
from janim.utils.file_ops import (find_file, find_file_in_path, get_janim_dir,
                                  readall)

_ = get_local_strings('shader')


def read_shader(file_path: str) -> str:
    lines = []
    found_path = find_shader_file(file_path)
    max_version = _read_shader(found_path, lines)
    return (
        f'#version {max_version} core\n'
        + '\n'.join(lines)
    )


def read_shader_or_none(file_path: str) -> str | None:
    lines = []
    try:
        found_path = find_shader_file(file_path)
    except FileNotFoundError:
        return None
    max_version = _read_shader(found_path, lines)
    return (
        f'#version {max_version} core\n'
        + '\n'.join(lines)
    )


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


_regex_version = re.compile(r'^\s*#\s*version\s+(\d+)\s+core\s*$')
_regex_include = re.compile(r'^\s*#\s*include\s+"([^"]+)"\s*$')
_regex_injection = re.compile(r'^\s*#\[\s*([^\]]+)\s*\]\s*$')


def _read_shader(file_path: str, lines: list[str]) -> int:
    path = Path(file_path).resolve()

    # 简化插入 glsl "#line" 的路径
    rel_path = path
    try:
        rel_path = path.relative_to(get_janim_dir())
    except ValueError:
        try:
            rel_path = path.relative_to(Path.cwd())
        except ValueError:
            pass
    rel_path_str = repr(str(rel_path))

    return _preprocess_shader(rel_path_str, readall(file_path), lines, str(path.parent))


def preprocess_shader(name: str, source: str, dir_path: str | None = None) -> str:
    lines = []
    max_version = _preprocess_shader(name, source, lines, dir_path)
    return (
        f'#version {max_version} core\n'
        + '\n'.join(lines)
    )


def _preprocess_shader(name: str, source: str, lines: list[str], dir_path: str | None) -> int:
    max_version = 330
    lines.append(f'#line 1 "{name}"')

    for i, line in enumerate(source.splitlines(), start=1):
        # 匹配例如 #version 330 core，提取最大需求版本
        match = _regex_version.match(line)
        if match:
            max_version = max(max_version, int(match.group(1)))
            lines.append('')
            continue

        # 匹配例如 #include "xxx"
        match = _regex_include.match(line)
        if match:
            included_file = match.group(1)
            found_file = find_shader_file(included_file, dir_path)
            # 递归读取包含的文件
            included_max_version = _read_shader(found_file, lines)
            max_version = max(max_version, included_max_version)
            # 返回原先的文件，所以需要恢复行号
            lines.append(f'#line {i + 1} "{name}"')
            continue

        # 匹配例如 #[xxx]
        match = _regex_injection.match(line)
        if match:
            # 插入 injection
            _read_shader_from_injection(match.group(1), lines)
            # 返回原先的文件，所以需要恢复行号
            lines.append(f'#line {i + 1} "{name}"')
            continue

        lines.append(line)

    return max_version


_injection_ja_finish_up = '''    if (!JA_BLENDING) {
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

_injection_ja_finish_up_uniforms = '''uniform bool JA_BLENDING;
uniform sampler2D JA_FRAMEBUFFER;
'''

shader_injections_ctx: ContextVar[list[dict[str, str]]] = ContextVar("shader_injections_ctx")
shader_injections_ctx.set([{
    'JA_FINISH_UP': _injection_ja_finish_up,
    'JA_FINISH_UP_UNIFORMS': _injection_ja_finish_up_uniforms
}])


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
        raise ShaderInjectionNotFoundError(
            _('ShaderInjection not found: {name}')
            .format(name=name)
        )


def _read_shader_from_injection(name: str, lines: list[str]) -> None:
    lines.append(f'#line 1 "{repr(f"#[{name}]")}"')
    lines.extend(ShaderInjection.find(name).splitlines())
