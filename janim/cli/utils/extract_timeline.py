import ast
import inspect
import linecache
import sys
import types
from typing import Callable, Sequence

from janim.timeline import Timeline
from janim.cli.utils.prompt import (
    Category,
    Entry,
    MatchResult,
    MatchState,
    prompt_entries,
    prompt_entries_in_categories,
)
from janim.locale import get_translator
from janim.logger import log
from janim.utils.file_ops import STDIN_FILENAME

_ = get_translator('janim.cli.utils.extract_timeline')


def extract_timelines_from_module(
    module: types.ModuleType,
    timeline_names: Sequence[str],
    all: bool,
) -> list[type[Timeline]]:
    """
    根据指定的 ``module`` 向用户询问使用哪些 :class:`~.Timeline`
    """
    if not all and timeline_names:
        return parse_existing_timeline_names_from_module(module, timeline_names)

    classes = get_all_timelines_from_module(module)
    if len(classes) <= 1 or all:
        return classes

    if module.__file__ == STDIN_FILENAME:
        log.error(
            _(
                'Multiple timelines found in stdin input. '  #
                'Please specify timeline names with command line arguments.'
            )
        )
        return []

    entries = [Entry(timeline_class.__name__, timeline_class) for timeline_class in classes]

    print(
        _('That module has multiple timelines, which ones would you like to render?'),
        file=sys.stderr,
    )
    results = prompt_entries(
        entries, _('Timeline Name or Number: '), subtitle=module.__file__, subtitle_align='right'
    )
    return parse_prompt_results(results)


def extract_timelines_from_modules(
    modules: list[tuple[str, types.ModuleType]],
    timeline_names: Sequence[str],
) -> list[type[Timeline]]:
    if timeline_names:
        return parse_existing_timeline_names_from_modules(
            [module for _, module in modules], timeline_names
        )

    categories: list[Category] = []
    for name, module in modules:
        assert module.__name__ != STDIN_FILENAME
        classes = get_all_timelines_from_module(module)
        categories.append(
            Category(
                name,
                [Entry(cls.__name__, cls) for cls in classes],
            )
        )

    print(
        _('There are multiple timelines, which ones would you like to render?'),
        file=sys.stderr,
    )
    results = prompt_entries_in_categories(categories, _('Timeline Name or Number: '))
    return parse_prompt_results(results)


def parse_existing_timeline_names_from_module(
    module: types.ModuleType,
    timeline_names: Sequence[str],
) -> list[type[Timeline]]:
    timelines: list[type[Timeline]] = []
    err: bool = False

    for name in timeline_names:
        try:
            timeline = module.__dict__[name]
            if not isinstance(timeline, type) or not issubclass(timeline, Timeline):
                raise KeyError()
            timelines.append(timeline)
        except KeyError:
            log.error(_('No timeline named "{name}"').format(name=name))
            err = True

    return [] if err else timelines


def parse_existing_timeline_names_from_modules(
    modules: list[types.ModuleType],
    timeline_names: Sequence[str],
) -> list[type[Timeline]]:
    timelines: list[type[Timeline]] = []
    err: bool = False

    for name in timeline_names:
        found: bool = False

        for module in modules:
            timeline = module.__dict__.get(name, None)
            if timeline is None:
                continue
            if not isinstance(timeline, type) or not issubclass(timeline, Timeline):
                continue
            timelines.append(timeline)
            found = True
            break

        if not found:
            log.error(_('No timeline named "{name}"').format(name=name))
            err = True

    return [] if err else timelines


def parse_prompt_results(results: list[MatchResult]) -> list[type[Timeline]]:
    timelines: list[type[Timeline]] = []
    err: bool = False

    if not results:
        print(_('Cancelled'), file=sys.stderr)
    else:
        for result in results:
            match result.state:
                case MatchState.Matched:
                    timelines.append(result.data)
                case MatchState.InvalidNumber:
                    log.error(_('Invaild number {num}').format(num=result.data))
                    err = True
                case MatchState.InvalidKeyword:
                    log.error(_('No timeline named "{name}"').format(name=result.data))
                    err = True

    return [] if err else timelines


def get_all_timelines_from_module(module) -> list[type[Timeline]]:
    """
    从指定的 ``module`` 中得到所有可用的 :class:`~.Timeline`

    会缓存结果，如果 ``module`` 的内容有更新可能需要使用 ``get_all_timelines_from_module.cache_clear()`` 来清空缓存
    """
    classes = [
        value
        for value in module.__dict__.values()
        if (
            isinstance(value, type)
            and issubclass(value, Timeline)
            # 定义于当前模块，排除了 import 导入的
            and value.__module__ == module.__name__
            # 排除以下划线开头的
            and not value.__name__.startswith('_')
            # construct 方法已被实现
            and not getattr(value.construct, '__isabstractmethod__', False)
        )
    ]
    if len(classes) <= 1:
        return classes

    lineno_key = get_lineno_key_function(module)

    if lineno_key is not None:
        classes.sort(key=lineno_key)

    return classes


def get_lineno_key_function(module) -> Callable[[type], tuple[int, int]] | None:
    """
    返回一个函数，其对于列表中的每个类：

    - 如果能找到 class 在 module 中所定义的行数，则返回 ``(0, 行数)``
    - 如果找不到，则返回 ``(1, 0)``

    **特殊情况说明：**

    对于重新载入的 module，如果代码里删除了某个类的代码，这个类仍然会出现在 module 中，
    但此时无法在 module 源代码中找到这个类的定义，所以把找不到的类返回 ``(1, 0)``，这样依据这个进行排序就会将其排序到最后

    更多技术细节请参阅 https://github.com/jkjkil4/JAnim/pull/36
    """
    file = inspect.getfile(module)
    if not file:
        return None

    # 模仿 inspect.findsource 的做法
    linecache.checkcache(file)
    lines = linecache.getlines(file, module.__dict__)
    if not lines:
        return None

    source = ''.join(lines)
    tree = ast.parse(source)

    collector = _ClassDefCollector()
    collector.visit(tree)

    defs = collector.defs

    def lineno_key(cls: type) -> tuple[int, int]:
        lineno = defs.get(cls.__name__, None)
        if lineno is None:
            return (1, 0)
        return (0, lineno)

    return lineno_key


class _ClassDefCollector(ast.NodeVisitor):
    def __init__(self):
        self.defs: dict[str, int] = {}

    def visit_ClassDef(self, node: ast.ClassDef):
        # 因为我们只关心最后一次定义的位置，所以直接赋值就行
        self.defs[node.name] = node.lineno
        # 由于只关心最顶层的 classdef，所以不需要 generic_visit
