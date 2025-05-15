import builtins
import importlib
import sys
from contextlib import contextmanager

builtin_import = builtins.__import__


@contextmanager
def reloads():
    builtins.__import__ = _reload_import_hook
    try:
        yield
    finally:
        builtins.__import__ = builtin_import


@contextmanager
def _disable_reloads():
    builtins.__import__ = builtin_import
    try:
        yield
    finally:
        builtins.__import__ = _reload_import_hook


def _reload_import_hook(name, globals=None, locals=None, fromlist=(), level=0):
    # 如果 name 在 sys.modules 中，则重新加载它
    module = sys.modules.get(name, None)
    if module is not None and hasattr(module, '__file__'):
        with _disable_reloads():
            importlib.reload(module)
        return module

    with _disable_reloads():
        return builtin_import(name, globals, locals, fromlist, level)
