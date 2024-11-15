from __future__ import annotations

import copy
import inspect
import itertools as it
import types
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterable, Self, overload

from janim.components.component import CmptInfo, Component, _CmptGroup
from janim.components.depth import Cmpt_Depth
from janim.exception import AsTypeError, CopyError, GetItemError
from janim.items.relation import Relation
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.base import Renderer
from janim.typing import SupportsApartAlpha
from janim.utils.data import AlignedData
from janim.utils.iterables import resize_preserving_order
from janim.utils.paths import PathFunc, straight_path

if TYPE_CHECKING:
    import moderngl as mgl
    from janim.items.points import Group

_ = get_local_strings('item')

type DynamicItem = Callable[[float], Item]

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

    renderer_cls = Renderer
    '''
    覆盖该值以在子类中使用特定的渲染器
    '''

    global_renderer: dict[tuple[type, mgl.Context], Renderer] = {}
    '''
    共用的渲染器，用于 ``is_temporary=True`` 的物件
    '''

    depth = CmptInfo(Cmpt_Depth[Self], 0)

    def __init__(
        self,
        *args,
        children: list[Item] | None = None,
        **kwargs
    ):
        super().__init__(*args)

        self.stored: bool = False
        self.stored_parents: list[Item] | None = None
        self.stored_children: list[Item] | None = None

        # 如果 is_temporary 为 True，则不会另外创建渲染器，而是使用共用的渲染器
        self.is_temporary: bool = False

        from janim.anims.timeline import Timeline
        self.timeline = Timeline.get_context(raise_exc=False)

        self._astype: type[Item] | None = None
        self._astype_mock_cmpt: dict[str, Component] = {}

        self._fix_in_frame = False
        self.renderer: Renderer | None = None

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

    def digest_styles(self, **styles) -> None:
        from janim.utils.deprecation import deprecated
        deprecated(
            'Item.digest_styles',
            'Item.set',
            remove=(2, 3)
        )
        self.set(**styles)

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

    def set_style(
        self,
        depth: float | None = None,
        **kwargs
    ) -> Self:
        from janim.utils.deprecation import deprecated
        deprecated(
            'Item.set_style',
            'Item.apply_style',
            remove=(2, 3)
        )
        self.apply_style(depth, **kwargs)

    def do(self, func: Callable[[Self], Any]) -> Self:
        '''
        使用 ``func`` 对物件进行操作，并返回 ``self`` 以方便链式调用
        '''
        func(self)
        return self

    def is_null(self) -> bool:
        return False

    @property
    def anim(self) -> Self:
        '''
        例如：

        .. code-block:: python

            self.play(
                item.anim.points.scale(2).r.color.set('green')
            )

        该例子会创建将 ``item`` 缩放 2 倍并且设置为绿色的补间动画

        并且可以向动画传入参数：

        .. code-block:: python

            self.play(
                item.anim(duration=2, rate_func=linear)
                .points.scale(2).r.color.set('green')
            )

        ``.r`` 表示从组件回到物件，这样就可以调用其它组件的功能
        '''
        from janim.anims.transform import MethodTransformArgsBuilder
        return MethodTransformArgsBuilder(self)

    # 使得 .anim() 后仍有代码提示
    @overload
    def __call__(self, **kwargs) -> Self: ...

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

    def astype[T](self, cls: type[T]) -> T:
        '''
        使得可以调用当前物件中没有的组件

        例：

        .. code-block:: python

            group = Group(
                Rect()
                Circle()
            )

        在这个例子中，并不能 ``group.color.set(BLUE)`` 来设置子物件中的颜色，
        但是可以使用 ``group.astype(VItem).color.set(BLUE)`` 来做到

        也可以使用简写 ``group(VItem).color.set(BLUE)``
        '''
        if not isinstance(cls, type) or not issubclass(cls, Item):
            raise AsTypeError(
                _('{name} is not based on Item class and cannot be used as an argument for astype')
                .format(name=cls.__name__)
            )

        self._astype = cls
        return self

    @overload
    def __call__[T](self, cls: type[T]) -> T: ...

    def __call__[T](self, cls: type[T]) -> T:
        '''
        等效于调用 ``astype``
        '''
        return self.astype(cls)

    def __getattr__(self, name: str):
        if name == '__setstate__':
            raise AttributeError()

        mockable_or_cmpt_info = None if self._astype is None else getattr(self._astype, name, None)

        if isinstance(mockable_or_cmpt_info, Callable) and getattr(mockable_or_cmpt_info, MOCKABLE_NAME, False):
            return types.MethodType(mockable_or_cmpt_info, self)

        cmpt_info = mockable_or_cmpt_info
        if not isinstance(cmpt_info, CmptInfo):
            super().__getattribute__(name)  # raise error

        # 找到 cmpt_info 是在哪个类中被定义的
        decl_cls: type[Item] | None = None
        for sup in self._astype.mro():
            if name in sup.__dict__.get(CLS_CMPTINFO_NAME, {}):
                decl_cls = sup

        assert decl_cls is not None

        # 如果 self 本身就是 decl_cls 的实例
        # 那么自身肯定有名称为 name 的组件，对于这种情况实际上完全没必要 astype
        # 为了灵活性，这里将这个已有的组件返回
        if isinstance(self, decl_cls):
            return getattr(self, name)

        cmpt = self._astype_mock_cmpt.get(name, None)

        # 如果 astype 需求的组件已经被创建过，并且新类型不是旧类型的子类，那么直接返回
        if cmpt is not None and (not issubclass(cmpt_info.cls, cmpt.__class__) or cmpt_info.cls is cmpt.__class__):
            return cmpt

        # astype 需求的组件还没创建，那么创建并记录
        cmpt = cmpt_info.create()
        cmpt.init_bind(Component.BindInfo(decl_cls, self, name))

        self._astype_mock_cmpt[name] = cmpt
        return cmpt

    # endregion

    # region data

    def get_parents(self):
        return self.stored_parents if self.stored else self.parents

    def get_children(self):
        return self.stored_children if self.stored else self.children

    def not_changed(self, other: Self) -> bool:
        if self.get_children() != other.get_children():
            return False
        for key, cmpt in self.components.items():
            if not cmpt.not_changed(other.components[key]):
                return False
        return True

    def current(self, *, as_time: float | None = None, skip_dynamic=False) -> Self:
        '''
        当前物件

        - 如果此时在回放和 Updater 中，则返回对应时间的历史物件
        - 在其余情况下，包括该物件没有历史记录的情况，则返回物件自身
        '''
        return self.timeline.item_current(self, as_time=as_time, skip_dynamic=skip_dynamic)

    def copy(self, *, root_only=False, as_time: float | None = None, skip_dynamic: bool = False) -> Self:
        '''
        复制物件
        '''
        if root_only and as_time is not None:
            raise CopyError(_('When root_only is set to True, as_time cannot be specified. '
                              'Please use ".current(as_time=...).store()" instead.'))

        copy_item = copy.copy(self)

        copy_item.reset_refresh()

        src = self if as_time is None else self.current(as_time=as_time, skip_dynamic=skip_dynamic)

        copy_item.parents = []
        copy_item.children = []
        if root_only:
            copy_item.stored = True
            copy_item.stored_parents = self.get_parents().copy()
            copy_item.stored_children = self.get_children().copy()
        else:
            copy_item.add(*[item.copy(as_time=as_time, skip_dynamic=skip_dynamic) for item in src.get_children()])
            copy_item.parents_changed()

        new_cmpts = {}
        for key, cmpt in src.components.items():
            if isinstance(cmpt, _CmptGroup):
                # 因为现在的 Python 版本中，dict 取键值保留原序
                # 所以 new_cmpts 肯定有 _CmptGroup 所需要的
                cmpt_copy = cmpt.copy(new_cmpts=new_cmpts)
            else:
                cmpt_copy = cmpt.copy()

            if cmpt.bind is not None:
                cmpt_copy.init_bind(Component.BindInfo(cmpt.bind.decl_cls,
                                                       copy_item,
                                                       key))

            new_cmpts[key] = cmpt_copy
            setattr(copy_item, key, cmpt_copy)

        copy_item.components = new_cmpts
        copy_item._astype_mock_cmpt = {}

        return copy_item

    # TODO: optimize
    def _current_family(self, *, up: bool) -> list[Item]:   # use DFS
        lst = self.stored_parents if up else self.stored_children
        res = []

        for sub_obj in lst:
            current = sub_obj.current()
            if current not in res:
                res.append(current)
            res.extend(filter(
                lambda obj: obj not in res,
                current._current_family(up=up)
                if current.stored
                else (current.ancestors() if up else current.descendants())
            ))

        return res

    def become(self, other: Item) -> Self:
        '''
        将该物件的数据设置为与传入的物件相同（以复制的方式，不是引用）
        '''
        # self.parents 不变

        children = self.children.copy()
        self.clear_children()
        for old, new in it.zip_longest(children, other.children):
            if new is None:
                break
            if old is None or type(old) is not type(new):
                self.add(new.copy())
            else:
                self.add(old.become(new))

        for key in self.components.keys() | other.components.keys():
            self.components[key].become(other.components[key])

        from janim.anims.timeline import Timeline
        timeline = Timeline.get_context(raise_exc=False)
        if timeline is not None and timeline.is_displaying(self):
            timeline.show(self)

        return self

    def store(self) -> Self:
        return self.copy(root_only=True)

    def restore(self, other: Item) -> Self:
        if self.stored:
            self.stored_parents = other.get_parents().copy()
            self.stored_children = other.get_children().copy()
        else:
            self.parents = other.get_parents().copy()
            self.parents_changed()
            self.children = other.get_parents().copy()
            self.children_changed()

        for key in self.components.keys() & other.components.keys():
            self.components[key].become(other.components[key])

        return self

    @classmethod
    def align_for_interpolate(
        cls,
        item1: Item,
        item2: Item
    ) -> AlignedData[Self]:
        '''
        进行数据对齐，以便插值
        '''
        aligned = AlignedData(item1.store(),
                              item1.store(),
                              item2.store())

        # align components
        for key, cmpt1 in item1.components.items():
            cmpt2 = item2.components.get(key, None)

            if isinstance(cmpt1, _CmptGroup) and isinstance(cmpt2, _CmptGroup):
                cmpt_aligned = cmpt1.align(cmpt1, cmpt2, aligned)

            elif cmpt2 is None:
                cmpt_aligned = AlignedData(cmpt1, cmpt1, cmpt1)
            else:
                cmpt_aligned = cmpt1.align_for_interpolate(cmpt1, cmpt2)

            aligned.data1.set_component(key, cmpt_aligned.data1)
            aligned.data2.set_component(key, cmpt_aligned.data2)
            aligned.union.set_component(key, cmpt_aligned.union)

        # align children
        max_len = max(len(item1.get_children()), len(item2.get_children()))
        aligned.data1.stored_children = resize_preserving_order(item1.get_children(), max_len)
        aligned.data2.stored_children = resize_preserving_order(item2.get_children(), max_len)

        return aligned

    def interpolate(
        self,
        item1: Item,
        item2: Item,
        alpha: float,
        *,
        path_func: PathFunc = straight_path,
    ) -> None:
        '''
        进行插值（仅对该物件进行，不包含后代物件）
        '''
        for key, cmpt in self.components.items():
            try:
                cmpt1 = item1.components[key]
                cmpt2 = item2.components[key]
            except KeyError:
                continue
            cmpt.interpolate(cmpt1, cmpt2, alpha, path_func=path_func)

    def apart_alpha(self, n: int) -> None:
        for cmpt in self.components.values():
            if isinstance(cmpt, SupportsApartAlpha):
                cmpt.apart_alpha(n)

    def fix_in_frame(self, on: bool = True, *, root_only: bool = False) -> Self:
        '''
        固定在屏幕上，也就是即使摄像头移动位置也不会改变在屏幕上的位置
        '''
        for item in self.walk_self_and_descendants(root_only):
            item._fix_in_frame = on
        return self

    def is_fix_in_frame(self) -> bool:
        return self._fix_in_frame

    @classmethod
    def get_global_renderer(cls) -> None:
        key = (cls, Renderer.data_ctx.get().ctx)
        renderer = cls.global_renderer.get(key, None)
        if renderer is None:
            renderer = cls.global_renderer[key] = cls.renderer_cls()
        return renderer

    def create_renderer(self) -> None:
        if self.is_temporary:
            self.renderer = self.get_global_renderer()
        else:
            self.renderer = self.renderer_cls()

    def render(self) -> None:
        if self.renderer is None:
            self.create_renderer()

        if not self.renderer.initialized:
            self.renderer.init()
            self.renderer.initialized = True
        self.renderer.render(self)

    # endregion

    # region timeline

    def show(self, **kwargs) -> Self:
        '''
        显示物件
        '''
        self.timeline.show(self, **kwargs)
        return self

    def hide(self, **kwargs) -> Self:
        '''
        隐藏物件
        '''
        self.timeline.hide(self, **kwargs)
        return self

    # endregion
