# 与 janim/cli/utils/extract_timeline.py 的对应函数相同

import ast
import inspect
import linecache
from typing import Callable

from janim.imports import Timeline


def get_all_timelines_from_module(module) -> list[type[Timeline]]:
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
