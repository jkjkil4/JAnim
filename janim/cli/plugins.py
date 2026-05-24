from importlib.metadata import entry_points
import types
from typing import Any, Callable
from dataclasses import dataclass

from janim.locale import get_translator
from janim.logger import log

_ = get_translator('janim.cli.plugins')


@dataclass
class PluginInfo:
    name: str
    get_examples_module: Callable[[], types.ModuleType | None]


_loaded_plugins: list[PluginInfo] | None = None


def load_plugins() -> list[PluginInfo]:
    global _loaded_plugins
    if _loaded_plugins is not None:
        return _loaded_plugins

    _loaded_plugins = []

    for entry_point in entry_points(group='janim.plugins'):
        name = entry_point.name
        try:
            plugin = entry_point.load()
        except Exception as e:
            log.warning(
                _('Failed to load plugin "{name}":\n- {exception}').format(
                    name=name,
                    exception=repr(e),
                ),
            )
            continue

        info = PluginInfo(
            name,
            getter_wrapper(name, plugin, 'get_examples_module', types.ModuleType),
        )
        _loaded_plugins.append(info)

    return _loaded_plugins


def getter_wrapper[T](
    name: str, plugin: Any, key: str, return_type: type[T]
) -> Callable[[], T | None]:

    def wrapper() -> T | None:
        try:
            getter = getattr(plugin, key, None)
            if getter is None:
                return None
            if not callable(getter):
                log.warning(
                    _('Plugin "{name}" has attribute "{key}", but it is not callable').format(
                        name=name,
                        key=key,
                    )
                )
                return None

            ret = getter()
            if not isinstance(ret, return_type):
                log.warning(
                    _(
                        '{key}() in plugin "{name}" returns incompatible type {actual}, expected {expected}'
                    ).format(
                        key=key,
                        name=name,
                        actual=type(ret),
                        expected=return_type,
                    )
                )
                return None

            return ret

        except Exception as e:
            log.warning(
                _('Failed to invoke {key}() in plugin "{name}":\n- {exception}').format(
                    key=key,
                    name=name,
                    exception=repr(e),
                )
            )

    return wrapper
