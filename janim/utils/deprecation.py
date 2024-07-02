from janim import __version__
from janim.logger import log

type VersionTuple = tuple[int, int]


def _get_version_tuple() -> VersionTuple:
    dot1 = __version__.index('.')
    dot2 = __version__.index('.', dot1 + 1)
    return (
        int(__version__[:dot1]),
        int(__version__[dot1 + 1: dot2])
    )


_version_tuple = _get_version_tuple()

_DEPRECATED_MSG = '{name!r} is deprecated and will be removed in JAnim {remove}'


def deprecated(name, message=_DEPRECATED_MSG, *, remove: tuple[int, int]):
    remove_formatted = f"{remove[0]}.{remove[1]}"
    if (_version_tuple[0] > remove[0]) or (_version_tuple[0] == remove[0] and _version_tuple[1] >= remove[1]):
        msg = f'{name!r} has been deprecated and removed since JAnim {remove_formatted}'
        raise RuntimeError(msg)
    else:
        msg = message.format(name=name, remove=remove_formatted)
        log.warning(msg, stacklevel=3)
