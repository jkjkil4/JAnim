from __future__ import annotations

from collections import defaultdict
import re
from typing import TYPE_CHECKING, Any, Callable, Concatenate, Sequence

from janim.constants import ORIGIN
from janim.exception import ColorNotFoundError
from janim.locale import get_translator
from janim.logger import log
from janim.typing import JAnimColor

if TYPE_CHECKING:
    from janim.items.text import TextChar

_ = get_translator('janim.items.text')


def _get_color_value(key: str) -> JAnimColor:
    """
    根据 ``key`` 从 ``janim.constants.colors`` 得到颜色

    如果 ``key`` 以 ``#`` 开头，则直接返回原值
    """
    if key.startswith('#'):
        return key

    import janim.constants.colors as colors

    if not hasattr(colors, key):
        raise ColorNotFoundError(_('No built-in color named {key}').format(key=key))
    return getattr(colors, key)


type ActConverter = Callable[[str], Any]
type ActCaller = Callable[Concatenate[TextChar, ...], Any]
type Act = tuple[Sequence[ActConverter], ActCaller]
type ActName = str

type ActParams = list[str]
type ActParamsStack = list[ActParams]

type ActAt = int
type ActStart = tuple[ActName, ActParams]
type ActEnd = str

_registered_acts: dict[ActName, list[Act]] = defaultdict(list)


def _register_acts(names: list[ActName], *acts: Act) -> None:
    """
    用于声明可用的富文本格式
    """
    for name in names:
        _registered_acts[name].extend(acts)


# fmt: off
_register_acts(
    ['color', 'c'],
    ((_get_color_value,),           lambda char, color: char.color.set(color)),
    ((float, float, float),         lambda char, r, g, b: char.color.set([r, g, b])),
    ((float, float, float, float),  lambda char, r, g, b, a: char.color.set_rgbas([[r, g, b, a]]))
)
_register_acts(
    ['stroke_color', 'sc'],
    ((_get_color_value,),           lambda char, color: char.stroke.set(color)),
    ((float, float, float),         lambda char, r, g, b: char.stroke.set([r, g, b])),
    ((float, float, float, float),  lambda char, r, g, b, a: char.stroke.set_rgbas([[r, g, b, a]]))
)
_register_acts(
    ['fill_color', 'fc'],
    ((_get_color_value,),           lambda char, color: char.fill.set(color)),
    ((float, float, float),         lambda char, r, g, b: char.fill.set([r, g, b])),
    ((float, float, float, float),  lambda char, r, g, b, a: char.fill.set_rgbas([[r, g, b, a]]))
)
_register_acts(
    ['alpha', 'a'],
    ((float,), lambda char, a: char.color.set(alpha=a))
)
_register_acts(
    ['stroke_alpha', 'sa'],
    ((float,), lambda char, a: char.stroke.set(alpha=a))
)
_register_acts(
    ['fill_alpha', 'fa'],
    ((float,), lambda char, a: char.fill.set(alpha=a))
)
_register_acts(
    ['stroke', 's'],
    ((float,), lambda char, radius: char.radius.set(radius))
)
_register_acts(
    ['font_scale', 'fs'],
    ((float,), lambda char, factor: char.points.scale(factor, about_point=ORIGIN))
)
# fmt: on


def extract_act_queue(source: str) -> tuple[str, ActQueue]:
    """
    按照 JAnim :class:`~.Text` 的富文本格式提取出所有的富文本标签，组成 :class:`~.ActQueue` 对象

    :return: ``(剔除富文本标签后的文本, ActQueue对象)``
    """

    text = ''
    acts: list[tuple[ActAt, ActStart | ActEnd]] = []

    prev_end = 0
    iter = re.finditer(r'<<|<(\/?[^>]*)>', source)
    for match in iter:
        match: re.Match
        start, end = match.span()
        text += source[prev_end:start]
        prev_end = end

        groups = match.groups()

        if groups[0] is None:  # << 转义
            text += '<'
        else:
            act = groups[0]
            if act.startswith('/'):
                acts.append((len(text), act[1:]))
            else:
                split = act.split()
                acts.append((len(text), (split[0], split[1:])))

    text += source[prev_end:]

    return (text, ActQueue(acts))


class ActQueue:
    def __init__(self, acts: list[tuple[ActAt, ActStart | ActEnd]]):
        self._acts = acts
        self._active_acts: defaultdict[str, ActParamsStack] = defaultdict(list)

    def advance_to(self, text_at: ActAt) -> None:
        """
        应用所有在 ``text_at`` 及之前的富文本标签，计入 ``self._active_acts``
        """
        # 处理所有 act_at <= text_at 的 act
        while self._acts and self._acts[0][0] <= text_at:
            next_act = self._acts.pop(0)[1]

            if isinstance(next_act, str):  # ActEnd
                stack = self._active_acts[next_act]
                try:
                    stack.pop()
                except IndexError:
                    log.warning(_('Unmatched end tag "</{name}>", ignored.').format(name=next_act))
                if not stack:
                    del self._active_acts[next_act]
            else:  # ActStart
                name, params = next_act
                self._active_acts[name].append(params)

    def apply_to(self, char: TextChar) -> None:
        """
        将当前的 ``self._acitve_acts`` 中，即生效中的富文本标签应用到 ``char`` 物件上
        """
        for name, stack in self._active_acts.items():
            params = stack[-1]
            if name not in _registered_acts:
                log.warning(
                    _('"{name}" is not a valid rich text tag. ("<{name} {params}>")').format(
                        name=name, params=' '.join(params)
                    )
                )
                continue

            for converters, caller in _registered_acts[name]:
                if len(converters) == len(params):
                    try:
                        caller(
                            char,
                            *[converter(param) for converter, param in zip(converters, params)],
                        )
                    except Exception:
                        log.error(
                            _(
                                'While applying {name}, {params} did not match with {cvt_names}.'
                            ).format(
                                name=name,
                                params=params,
                                cvt_names=[cvt.__name__ for cvt in converters],
                            )
                        )
                        raise

                    break
            else:
                txt = ','.join(
                    [
                        '[' + ','.join([cvt.__name__ for cvt in act[0]]) + ']'
                        for act in _registered_acts[name]
                    ]
                )
                log.warning(
                    _('While applying "{name}", {params} did not match any entry in {txt}.').format(
                        name=name, params=params, txt=txt
                    )
                )
