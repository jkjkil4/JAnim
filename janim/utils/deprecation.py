from janim import __version__
from janim.logger import log
from janim.locale.i18n import get_local_strings

_ = get_local_strings('deprecation')

type VersionTuple = tuple[int, int]


def _get_version_tuple() -> VersionTuple:
    dot1 = __version__.index('.')
    dot2 = __version__.index('.', dot1 + 1)
    return (
        int(__version__[:dot1]),
        int(__version__[dot1 + 1: dot2])
    )


_version_tuple = _get_version_tuple()

_DEPRECATED_MSG = _('{name!r} is deprecated and will be removed in JAnim {remove}')
_DEPRECATED_MSG_I = _('{name!r} is deprecated and will be removed in JAnim {remove}, use {instead!r} instead')


def deprecated(name, instead=None, *, remove: tuple[int, int]):
    remove_formatted = f"{remove[0]}.{remove[1]}"
    if (_version_tuple[0] > remove[0]) or (_version_tuple[0] == remove[0] and _version_tuple[1] >= remove[1]):
        msg = f'{name!r} has been deprecated and removed since JAnim {remove_formatted}'
        raise RuntimeError(msg)
    else:
        if instead is None:
            msg = _DEPRECATED_MSG.format(name=name, remove=remove_formatted)
        else:
            msg = _DEPRECATED_MSG_I.format(name=name, remove=remove_formatted, instead=instead)
        log.warning(msg, stacklevel=3)
