import builtins
import importlib
import sys
from contextlib import contextmanager

_builtin_import = builtins.__import__


@contextmanager
def reloads():
    '''
    在一般情况下，使用 import 导入时，已经加载过的模块不会重新加载，导致 :ref:`重新构建 <realtime_preview>` 时无法响应外部文件的变化。

    例如在以下代码中，重新构建时无法响应 ``your_custom_module`` 中产生的更改

    .. code-block:: python

        from janim.imports import *

        from your_custom_module import *

    此时可以使用 ``with reloads():`` 强制其中的 import 语句重新加载模块，
    使得可以响应外部文件的更改，如以下代码所示

    .. code-block:: python

        from janim.imports import *

        with reloads():
            from your_custom_module import *
    '''
    builtins.__import__ = _reload_import_hook
    try:
        yield
    finally:
        builtins.__import__ = _builtin_import


@contextmanager
def _disable_reloads():
    builtins.__import__ = _builtin_import
    try:
        yield
    finally:
        builtins.__import__ = _reload_import_hook


_loaded_modules: list[str] = []


def reset_reloads_state() -> None:
    _loaded_modules.clear()


def _reload_import_hook(name, globals=None, locals=None, fromlist=(), level=0):
    with _disable_reloads():
        # 如果 name 在这一次重新构建过程中已经被重新加载过了，那么就不需要再重新加载，直接 import
        if name in _loaded_modules:
            return _builtin_import(name, globals, locals, fromlist, level)

        # 如果 name 在 sys.modules 中，则重新加载它
        module = sys.modules.get(name, None)
        if module is not None and hasattr(module, '__file__'):
            importlib.reload(module)
            _loaded_modules.append(name)
            return module

        # 对于没有加载过的，直接调用内置 import 进行加载
        module = _builtin_import(name, globals, locals, fromlist, level)
        _loaded_modules.append(name)
        return module
