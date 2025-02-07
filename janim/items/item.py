from __future__ import annotations

import inspect
import itertools as it
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterable, Self, overload

from janim.components.component import CmptInfo, Component
from janim.components.depth import Cmpt_Depth
from janim.exception import GetItemError
from janim.items.relation import Relation
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.typing import SupportsApartAlpha

if TYPE_CHECKING:
    from janim.items.points import Group

_ = get_local_strings('item')

CLS_CMPTINFO_NAME = '__cls_cmptinfo'
CLS_STYLES_NAME = '__cls_styles'
ALL_STYLES_NAME = '__all_styles'
MOCKABLE_NAME = '__mockable'


class _ItemMeta(type):
    '''
    作为 metaclass 记录定义在类中的所有 CmptInfo
    '''
    def __new__(cls: type, name: str, bases: tuple[type, ...], attrdict: dict):
        # 记录所有定义在类中的 CmptInfo
        cls_components: dict[str, Component] = {
            key: val
            for key, val in attrdict.items()
            if isinstance(val, CmptInfo)
        }
        attrdict[CLS_CMPTINFO_NAME] = cls_components

        # 记录 apply_style 的参数
        apply_style_func = attrdict.get('apply_style', None)
        if apply_style_func is not None and callable(apply_style_func):
            sig = inspect.signature(apply_style_func)
            styles_name: list[str] = [
                param.name
                for param in list(sig.parameters.values())[1:]
                if param.kind not in (param.POSITIONAL_ONLY, param.VAR_POSITIONAL, param.VAR_KEYWORD)
            ]
            attrdict[CLS_STYLES_NAME] = styles_name

            all_styles = list(it.chain(
                styles_name,
                *[
                    getattr(base, CLS_STYLES_NAME)
                    for base in bases
                    if hasattr(base, CLS_STYLES_NAME)
                ]
            ))
            attrdict[ALL_STYLES_NAME] = all_styles

        return super().__new__(cls, name, bases, attrdict)

    @dataclass
    class _CmptInitData:
        info: CmptInfo[CmptInfo]
        decl_cls: type[Item]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cmpt_init_datas: dict[str, _ItemMeta._CmptInitData] = {}
        datas = self.cmpt_init_datas

        for cls in reversed(self.mro()):
            for key, info in cls.__dict__.get(CLS_CMPTINFO_NAME, {}).items():
                if key in datas:
                    datas[key].info = info
                else:  # key not in datas
                    datas[key] = self._CmptInitData(info, cls)


def mockable(func):
    '''
    使得 ``.astype`` 后可以调用被 ``@mockable`` 修饰的方法
    '''
    setattr(func, MOCKABLE_NAME, True)
    return func


class Item(Relation['Item'], metaclass=_ItemMeta):
    '''
    :class:`~.Item` 是物件的基类

    除了使用 ``item[0]`` ``item[1]`` 进行下标索引外，还可以使用列表索引和布尔索引

    - 列表索引，例如 ``item[0, 1, 3]``, 即 ``Group(item[0], item[1], item[3])``

    - 布尔索引，例如 ``item[False, True, False, True, True]`` 表示取出 ``Group(item[1], item[3], item[4])``，

      也就是将那些为 True 的位置取出组成一个 :class:`~.Group`
    '''

    # TODO: renderer_cls

    # TODO: global_renderer

    depth = CmptInfo(Cmpt_Depth[Self], 0)

    def __init__(
        self,
        *args,
        children: list[Item] | None = None,
        **kwargs
    ):
        super().__init__(*args)

        # TODO: self.stored
        # TODO: self.stored_parents
        # TODO: self.stored_children

        # TODO: self.is_temporary

        from janim.anims.timeline import Timeline
        self.timeline = Timeline.get_context(raise_exc=False)

        # TODO: self._astype
        # TODO: self._astype_mock_cmpt

        # TODO: self.fix_in_frae
        # TODO: self.renderer

        self._init_components()

        if children is not None:
            self.add(*children)
        self.set(**kwargs)

    def _init_components(self) -> None:
        '''
        创建出 CmptInfo 对应的 Component，
        并以同名存于对象中，起到在名称上覆盖类中的 CmptInfo 的效果

        因为 CmptInfo 的 __get__ 标注的返回类型是对应的 Component，
        所以以上做法没有影响基于类型标注的代码补全
        '''
        datas = self.__class__.cmpt_init_datas

        self.components: dict[str, Component] = {}

        for key, data in datas.items():
            obj = data.info.create()
            obj.init_bind(Component.BindInfo(data.decl_cls, self, key))

            self.__dict__[key] = self.components[key] = obj

    def set_component(self, key: str, cmpt: Component) -> None:
        setattr(self, key, cmpt)
        self.components[key] = cmpt

    def broadcast_refresh_of_component(
        self,
        cmpt: Component,
        func: Callable | str,
        recurse_up=False,
        recurse_down=False,
    ) -> Self:
        '''
        为 :meth:`~.Component.mark_refresh()`
        进行 ``recurse_up/down`` 的处理
        '''
        if not recurse_up and not recurse_down:
            return

        def mark(items: list[Item]):
            for item in items:
                if isinstance(item, cmpt.bind.decl_cls):
                    # 一般情况
                    item_cmpt: Component = getattr(item, cmpt.bind.key)
                    item_cmpt.mark_refresh(func)

                else:
                    # astype 情况
                    mock_cmpt = item._astype_mock_cmpt.get(cmpt.bind.key, None)
                    if mock_cmpt is not None:
                        mock_cmpt.mark_refresh(func)

        if recurse_up:
            mark(self.ancestors())

        if recurse_down:
            mark(self.descendants())

    def set(self, **styles) -> None:
        '''
        设置物件以及子物件的样式，与 :meth:`apply_styles` 只影响自身不同的是，该方法也会影响所有子物件
        '''
        flags = dict.fromkeys(styles.keys(), False)
        for item in self.walk_self_and_descendants():
            available_styles = item.get_available_styles()
            apply_styles = {
                key: style
                for key, style in styles.items()
                if key in available_styles
            }
            for key in apply_styles:
                flags[key] = True
            item.apply_style(**apply_styles)

        for key, flag in flags.items():
            if not flag:
                log.warning(
                    _('The passed parameter "{key}" did not match any style settings and was not used anywhere.')
                    .format(key=key)
                )

    @classmethod
    def get_available_styles(cls) -> list[str]:
        return getattr(cls, ALL_STYLES_NAME)

    def apply_style(
        self,
        depth: float | None = None,
        **kwargs
    ) -> Self:
        '''
        设置物件自身的样式，不影响子物件

        另见：:meth:`set`
        '''
        if depth is not None:
            self.depth.set(depth, root_only=True)
        return self

    def do(self, func: Callable[[Self], Any]) -> Self:
        '''
        使用 ``func`` 对物件进行操作，并返回 ``self`` 以方便链式调用
        '''
        func(self)
        return self

    def is_null(self) -> bool:
        return False

    # TODO: anim

    # TODO: override __call__

    @overload
    def __getitem__(self, key: int) -> Item: ...
    @overload
    def __getitem__(self, key: slice) -> Group: ...
    @overload
    def __getitem__(self, key: Iterable[int]) -> Group: ...
    @overload
    def __getitem__(self, key: Iterable[bool]) -> Group: ...

    def __getitem__(self, key):
        if isinstance(key, Iterable) and not isinstance(key, list):
            key = list(key)

        # example: item[0]
        if isinstance(key, int):
            return self.children[key]

        from janim.items.points import Group

        match key:
            # example: item[0:2]
            case slice():
                return Group(*self.children[key])
            # example: item[False, True, True]
            case list() if all(isinstance(x, bool) for x in key):
                return Group(*[sub for sub, flag in zip(self, key) if flag])
            # example: item[0, 3, 4]
            case list() if all(isinstance(x, int) for x in key):
                return Group(*[self.children[x] for x in key])

        raise GetItemError(_('Unsupported key: {}').format(key))

    def __iter__(self):
        return iter(self.children)

    def __len__(self) -> int:
        return len(self.children)

    def __mul__(self, other: int) -> Group[Self]:
        assert isinstance(other, int)
        return self.replicate(other)

    def replicate(self, n: int) -> Group[Self]:
        '''
        复制 n 个自身，并作为一个 :class:`Group` 返回

        可以将 ``item * n`` 作为该方法的简写
        '''
        from janim.items.points import Group
        return Group(
            *(self.copy() for i in range(n))
        )

    # region astype

    # TODO: astype

    # TODO: override __call__

    # TODO: __getattr__

    # endregion

    # region data

    # TODO: get_parents (请参考重构前的代码，这里只是为了功能而写了一个暂时性的代码)
    def get_parents(self):
        return self.parents

    # TODO: get_children（与 get_parents 同理）
    def get_children(self):
        return self.children

    def not_changed(self, other: Self) -> bool:
        if self.get_children() != other.get_children():
            return False
        for key, cmpt in self.components.items():
            if not cmpt.not_changed(other.components[key]):
                return False
        return True

    # TODO: current

    # TODO: copy

    # TODO: _current_family

    # TODO: become

    # TODO: store

    # TODO: restore

    # TODO: align_for_interpolate

    # TODO: interpolate

    def apart_alpha(self, n: int) -> None:
        for cmpt in self.components.values():
            if isinstance(cmpt, SupportsApartAlpha):
                cmpt.apart_alpha(n)

    # TODO: fix_in_frame

    # TODO: is_fix_in_frame

    # TODO: get_global_renderer

    # TODO: create_renderer

    # TODO: render

    # endregion

    # region timeline

    # TODO: show

    # TODO: hide

    # endregion
