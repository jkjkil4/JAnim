from __future__ import annotations

import copy
import inspect
import itertools as it
import types
from contextlib import contextmanager
from dataclasses import dataclass
from typing import (TYPE_CHECKING, Any, Callable, Iterable, Self,
                    SupportsIndex, overload)

import numpy as np

from janim.components.component import CmptInfo, Component, _CmptGroup
from janim.components.depth import Cmpt_Depth
from janim.exception import AsTypeError, GetItemError
from janim.items.relation import Relation
from janim.locale.i18n import get_translator
from janim.logger import log
from janim.render.base import Renderer
from janim.typing import SupportsApartAlpha
from janim.utils.data import AlignedData
from janim.utils.iterables import resize_preserving_order
from janim.utils.paths import PathFunc, straight_path
from janim.utils.signal import SIGNAL_OBJ_SLOTS_NAME

if TYPE_CHECKING:
    from janim.items.points import Group

_ = get_translator('janim.items.item')

CLS_CMPTINFO_NAME = '__cls_cmptinfo'
CLS_STYLES_NAME = '__cls_styles'
ALL_STYLES_NAME = '__all_styles'
MOCKABLE_NAME = '__mockable'


class _ItemMeta(type):
    """
    作为 metaclass 记录定义在类中的所有 CmptInfo
    """
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

        self._cmpt_init_datas: dict[str, _ItemMeta._CmptInitData] = {}
        datas = self._cmpt_init_datas

        for cls in reversed(self.mro()):
            for key, info in cls.__dict__.get(CLS_CMPTINFO_NAME, {}).items():
                if key in datas:
                    datas[key].info = info
                else:  # key not in datas
                    datas[key] = self._CmptInitData(info, cls)


def mockable(func):
    """
    使得 ``.astype`` 后可以调用被 ``@mockable`` 修饰的方法
    """
    setattr(func, MOCKABLE_NAME, True)
    return func


class Item(Relation['Item'], metaclass=_ItemMeta):
    """
    :class:`~.Item` 是物件的基类

    除了使用 ``item[0]`` ``item[1]`` 进行下标索引外，还可以使用列表索引和布尔索引

    - 列表索引，例如 ``item[0, 1, 3]``, 即 ``Group(item[0], item[1], item[3])``

    - 布尔索引，例如 ``item[False, True, False, True, True]`` 表示取出 ``Group(item[1], item[3], item[4])``，

      也就是将那些为 True 的位置取出组成一个 :class:`~.Group`
    """

    renderer_cls = Renderer

    depth = CmptInfo(Cmpt_Depth[Self], 0)

    # 在默认情况下为 None，会由子类（例如 `VItem`）使用
    #
    # @property
    # def distance_sort_refernece_point(self) -> np.ndarray | None: ...
    #
    # 来明确具体实现
    distance_sort_reference_point: np.ndarray | None = None

    def __init__(
        self,
        *args,
        children: list[Item] | None = None,
        **kwargs
    ):
        super().__init__(*args)

        self._stored: bool = False
        self._stored_parents: list[Item] | None = None
        self._stored_children: list[Item] | None = None

        from janim.anims.timeline import Timeline
        self.timeline = Timeline.get_context(raise_exc=False)

        self._astype_wrapper: Item._AsTypeWrapper | None = None
        self._astype_mock_cmpt: dict[str, Component] = {}

        self._fix_in_frame = False
        self._depth_test = False
        self._distance_sort = False

        self._saved_states: dict[str, Item.SavedState[Self]] = {}

        self._init_components()

        if children is not None:
            self.add(*children)
        self.set(**kwargs)

        self.init_connect()

    def init_connect(self) -> None:
        pass

    def _init_components(self) -> None:
        """
        创建出 CmptInfo 对应的 Component，
        并以同名存于对象中，起到在名称上覆盖类中的 CmptInfo 的效果

        因为 CmptInfo 的 __get__ 标注的返回类型是对应的 Component，
        所以以上做法没有影响基于类型标注的代码补全
        """
        datas = self.__class__._cmpt_init_datas

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
        """
        为 :meth:`~.Component.mark_refresh()`
        进行 ``recurse_up/down`` 的处理
        """
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

    def set(self, **styles) -> Self:
        """
        设置物件以及子物件的样式，与 :meth:`apply_styles` 只影响自身不同的是，该方法也会影响所有子物件
        """
        flags = dict.fromkeys(styles.keys(), False)
        renderable_count = 0
        for item in self.walk_self_and_descendants():
            available_styles = item.get_available_styles()
            apply_styles = {
                key: style
                for key, style in styles.items()
                if key in available_styles
            }
            item.apply_style(**apply_styles)

            # 记录哪些样式被应用了，以便在遍历所有后代物件后，警告未标记到的样式
            for key in apply_styles:
                flags[key] = True
            # 由于空 Group 本身就没有可应用的样式，所以对于空 Group 我们应当忽略对未使用样式的警告
            # 这里的处理方法是，如果自己以及所有后代物件都不是可渲染的，即 count==0，那么就忽略样式警告
            if item.renderer_cls is not Renderer:
                renderable_count += 1

        if renderable_count != 0:
            for key, flag in flags.items():
                if not flag:
                    log.warning(
                        _('The passed parameter "{key}" did not match any style settings and was not used anywhere.')
                        .format(key=key)
                    )

        return self

    @classmethod
    def get_available_styles(cls) -> list[str]:
        return getattr(cls, ALL_STYLES_NAME)

    def apply_style(
        self,
        depth: float | None = None,
        **kwargs
    ) -> Self:
        """
        设置物件自身的样式，不影响子物件

        另见：:meth:`set`
        """
        if depth is not None:
            self.depth.set(depth, root_only=True)
        return self

    def do(self, func: Callable[[Self], Any]) -> Self:
        """
        使用 ``func`` 对物件进行操作，并返回 ``self`` 以方便链式调用
        """
        func(self)
        return self

    def is_null(self) -> bool:
        return False

    @property
    def anim(self) -> Self:
        """
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
        """
        from janim.anims.transform import MethodTransformArgsBuilder
        return MethodTransformArgsBuilder(self)

    @property
    def update(self) -> Self:
        """
        例如：

        .. code-block:: python

            self.play(
                item.update.points.shift(RIGHT * 2),
                item.update(rate_func=rush_into).color.set(GREEN)
            )

        该例子会创建将 ``item`` 向右移动两个单位并且设置为绿色的 updater，并且二者的 ``rate_func`` 不同
        """
        from janim.anims.updater import MethodUpdaterArgsBuilder
        return MethodUpdaterArgsBuilder(self)

    # 仅用于在创建动画时忘记使用 .anim 或 .update 时抛出错误，另见 AnimGroup 的 _get_anim_object
    def __anim__(self):
        raise NotImplementedError()

    # 使得 .anim() .update() 后仍有代码提示
    @overload
    def __call__(self, **kwargs) -> Self: ...

    @overload
    def __getitem__(self, key: int) -> Item: ...
    @overload
    def __getitem__(self, key: slice | Iterable[int] | Iterable[bool]) -> Group: ...

    def __getitem__(self, key):
        if isinstance(key, Iterable) and not isinstance(key, list):
            key = list(key)

        # example: item[0]
        if isinstance(key, SupportsIndex):
            return self._children[key]

        from janim.items.points import Group

        match key:
            # example: item[0:2]
            case slice():
                return Group(*self._children[key])
            # example: item[False, True, True]
            case list() if all(isinstance(x, bool) for x in key):
                return Group(*[sub for sub, flag in zip(self, key) if flag])
            # example: item[0, 3, 4]
            case list() if all(isinstance(x, SupportsIndex) for x in key):
                return Group(*[self._children[x] for x in key])

        raise GetItemError(_('Unsupported key: {}').format(key))

    def __mul__(self, other: int) -> Group[Self]:
        assert isinstance(other, int)
        return self.replicate(other)

    def replicate(self, n: int) -> Group[Self]:
        """
        复制 n 个自身，并作为一个 :class:`~.Group` 返回

        可以将 ``item * n`` 作为该方法的简写
        """
        from janim.items.points import Group
        return Group(
            *(self.copy() for i in range(n))
        )

    def join[T](self, lst: Iterable[T]) -> Group[Self | T]:
        from janim.items.points import Group
        it = iter(lst)
        items = []
        try:
            items.append(next(it))
        except StopIteration:
            return Group()
        for item in it:
            items.append(self.copy())
            items.append(item)
        return Group(*items)

    # region astype

    class _AsTypeWrapper:
        def __init__(self, item: Item, obj: Item | Component | Callable, cls: type[Item]):
            self._astype_item = item

            self._astype_obj = obj
            self._astype_cls = cls

        # 调用 __anim__ 直接结束 Wrapper，返回内层的 __anim__ 调用
        def __anim__(self):
            return self._astype_obj.__anim__()

        def __getattr__(self, name: str):
            with self._astype_context():
                match self._astype_obj:
                    case Item():
                        attr = self._getattr_for_item(name)
                    case Component():
                        attr = self._getattr_for_cmpt(name)
                    case _:
                        attr = getattr(self._astype_obj, name)

            if not isinstance(attr, (Item, Component, Callable)):
                return attr

            return Item._AsTypeWrapper(self._astype_item, attr, self._astype_cls)

        def __call__(self, *args, **kwargs):
            with self._astype_context():
                attr = self._astype_obj(*args, **kwargs)

            if not isinstance(attr, (Item, Component, Callable)):
                return attr

            return Item._AsTypeWrapper(self._astype_item, attr, self._astype_cls)

        @contextmanager
        def _astype_context(self):
            prev = self._astype_item._astype_wrapper
            self._astype_item._astype_wrapper = self
            try:
                yield
            finally:
                self._astype_item._astype_wrapper = prev

        def _getattr_for_item(self, name: str):
            # 在物件级别获取属性，分为以下几种情况：
            # 获取组件：
            #   - 当物件本身存在 name 所指的组件时，直接返回
            #   - 当物件不存在 name 所指的组件时，创建 mock 组件返回
            # 获取方法：
            #   - 当物件本身存在 name 所指的方法时：
            #       - 如果 item.__class__ 是 cls 的子类，这意味着 item 比 cls 还更高级，那么就直接返回该方法
            #       - 如果相反，那么就在 cls.mro() 中寻找 mockable 方法，如果找不到或者回到了 item.__class__，则直接返回原方法
            #   - 当物件本身不存在 name 所指的方法时：
            #       在 cls.mro() 中寻找 mockable 方法，如果找不到或者回到了 item.__class__，则直接返回原方法
            # 获取其它属性：
            #   直接获取

            # 但是以上表述需要整理成以下形式方便处理（上面这段注释和下面这段注释是对同一流程的相同表述，只是结构上的区别）：
            # 当物件中存在 name 所指的属性时 (else)：
            #   - 如果是组件，直接返回
            #   - 如果是方法:
            #       - 如果 item.__class__ 是 cls 的子类，这意味着 Item 比 cls 还更高级，那么就直接返回该方法
            #       - 如果相反，那么就在 cls.mro() 中寻找 mockable 方法，如果找不到或者回到了 item.__class__，则直接返回原方法
            #   - 如果是其它属性：
            #       直接获取
            # 当物件中不存在 name 所指的属性时，那么在 cls 中查找 (except):
            #   - 如果在 cls 中是组件:
            #       则创建 mock 组件返回
            #   - 如果在 cls 中是方法:
            #       则在 cls.mro() 中寻找 mockable 方法，如果找不到或者回到了 item.__class__，则报错
            #   - 如果是其它属性:
            #       报错
            item = self._astype_obj
            itemcls = self._astype_obj.__class__
            try:
                attr = item.__getattribute__(name)
            except AttributeError:
                cls_attr = getattr(self._astype_cls, name, None)
                attr = None

                if isinstance(cls_attr, CmptInfo):
                    attr = self._get_mock_cmpt(cls_attr, name)
                elif isinstance(cls_attr, Callable):
                    attr = self._get_mockable_method(self._astype_cls, name, itemcls)

                if attr is None:
                    raise
            else:
                if isinstance(attr, Component):
                    pass
                elif isinstance(attr, Callable):
                    if not issubclass(itemcls, self._astype_cls):
                        ret = self._get_mockable_method(self._astype_cls, name, itemcls)
                        if ret is not None:
                            attr = ret
            return attr

        def _getattr_for_cmpt(self, name: str):
            # 当组件中存在 name 所指的属性时 (else):
            #   - 如果是方法:
            #       - 如果 astype 里有同名组件:
            #           - 如果 cmpt.__class__ 是 cmpt_info.cls 的子类，这意味着 item 比 cmpt_info.cls 还更高级，那么就直接返回该方法
            #           - 如果相反，那么就在 cmpt_info.cls.mro() 中寻找 mockable 方法，如果找不到或者回到了 cmptcls，则直接返回原方法
            #       - 如果 astype 里没有同名组件:
            #           直接返回
            #   - 如果是其它属性:
            #       直接返回
            # 当组件中不存在 name 所指的属性时 (except):
            #   - 如果 astype 里有同名组件:
            #       - 如果在 cmpt_info.cls 中是方法:
            #           则在 cmpt_info.cls.mro() 中寻找 mockable 方法，如果找不到或者回到了 cmptcls，则报错
            #       - 如果是其它属性:
            #           报错
            #   - 如果 astype 里没有同名组件:
            #       报错
            cmpt = self._astype_obj
            cmptcls = cmpt.__class__
            try:
                attr = getattr(cmpt, name)
            except AttributeError:
                cmpt_info: CmptInfo | None = getattr(self._astype_cls, cmpt.bind.key, None)
                if cmpt_info is None:
                    raise
                other_attr = getattr(cmpt_info.cls, name, None)
                if other_attr is None:
                    raise
                attr = self._get_mockable_method(cmpt_info.cls, name, cmptcls)
                if attr is None:
                    raise
            else:
                if isinstance(attr, Callable):
                    cmpt_info: CmptInfo | None = getattr(self._astype_cls, cmpt.bind.key, None)
                    if not issubclass(cmptcls, cmpt_info.cls):
                        ret = self._get_mockable_method(cmpt_info.cls, name, cmptcls)
                        if ret is not None:
                            attr = ret
            return attr

        def _get_mock_cmpt(self, cmpt_info: CmptInfo, name: str) -> Component:
            item = self._astype_obj

            # 找到 cmpt_info 是在哪个类中被定义的
            decl_cls: type[Item] | None = None
            for sup in self._astype_cls.mro():
                if name in sup.__dict__.get(CLS_CMPTINFO_NAME, {}):
                    decl_cls = sup

            assert decl_cls is not None

            cmpt = item._astype_mock_cmpt.get(name, None)

            # 如果 astype 需求的组件已经被创建过，并且新类型不是旧类型的子类，那么直接返回
            if cmpt is not None and issubclass(cmpt.__class__, cmpt_info.cls):
                return cmpt

            # astype 需求的组件还没创建，那么创建并记录
            cmpt = cmpt_info.create()
            cmpt.init_bind(Component.BindInfo(decl_cls, item, name))

            item._astype_mock_cmpt[name] = cmpt
            return cmpt

        def _get_mockable_method(self, base: type[Item], name: str, until: type[Item]) -> Callable | None:
            for sup in base.mro():
                if sup is until:
                    break
                method = getattr(sup, name, None)
                if method is None:
                    break
                if isinstance(method, Callable) and getattr(method, MOCKABLE_NAME, False):
                    return types.MethodType(method, self._astype_obj)
            return None

    def astype[T](self, cls: type[T]) -> T:
        """
        使得可以调用当前物件中没有的组件

        例：

        .. code-block:: python

            group = Group(
                Rect()
                Circle()
            )

        在这个例子中，并不能 ``group.color.set(BLUE)`` 来设置后代物件中的颜色，
        但是可以使用 ``group.astype(VItem).color.set(BLUE)`` 来做到

        也可以使用简写

        .. code-block:: python

            group(VItem).color.set(BLUE)
        """
        if not isinstance(cls, type) or not issubclass(cls, Item):
            raise AsTypeError(
                _('{name} is not based on Item class and cannot be used as an argument for astype')
                .format(name=cls.__name__)
            )

        return Item._AsTypeWrapper(self, self, cls)

    @overload
    def __call__[T](self, cls: type[T]) -> T: ...

    def __call__[T](self, cls: type[T]) -> T:
        """
        等效于调用 ``astype``
        """
        return self.astype(cls)

    def __getattr__(self, name: str):
        if name == '__setstate__':
            raise AttributeError()

        wrapper = self._astype_wrapper
        if wrapper is None:
            self.__getattribute__(name)

        new_wrapper = Item._AsTypeWrapper(wrapper._astype_item, wrapper._astype_item, wrapper._astype_cls)
        return getattr(new_wrapper, name)

    # endregion

    # region data

    def get_parents(self):
        return self._stored_parents if self._stored else self._parents

    def get_children(self):
        return self._stored_children if self._stored else self._children

    def not_changed(self, other: Self) -> bool:
        if self.get_children() != other.get_children():
            return False
        for key, cmpt in self.components.items():
            if not cmpt.not_changed(other.components[key]):
                return False
        return True

    def current(self, *, as_time: float | None = None, root_only=False) -> Self:
        """
        由当前时间点获得当前物件（考虑动画作用后的结果）
        """
        return self.timeline.item_current(self, as_time=as_time, root_only=root_only)

    @staticmethod
    def _copy_cmpts(src: Item, copy_item: Item) -> None:
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

    def copy(self, *, root_only: bool = False):
        """
        复制物件
        """
        copy_item = copy.copy(self)
        copy_item.reset_refresh()
        setattr(copy_item, SIGNAL_OBJ_SLOTS_NAME, None)

        copy_item._parents = []
        copy_item._children = []

        if root_only:
            copy_item._children_changed()
        else:
            # .add 里已经调用了 .children_changed
            copy_item.add(*[item.copy() for item in self])
        copy_item._parents_changed()

        self._copy_cmpts(self, copy_item)
        copy_item.init_connect()
        return copy_item

    def become(self, other: Item, *, auto_visible: bool = True) -> Self:
        """
        将该物件的数据设置为与传入的物件相同（以复制的方式，不是引用）
        """
        if self.timeline is not None:
            force_detect_items = set(self.walk_self_and_descendants())

        # self.parents 不变

        children = self._children.copy()
        self.clear_children()
        for old, new in it.zip_longest(children, other._children):
            if new is None:
                break
            if old is None or type(old) is not type(new):
                self.add(new.copy())
            else:
                self.add(old.become(new, auto_visible=auto_visible))

        for key in self.components.keys() | other.components.keys():
            self.components[key].become(other.components[key])

        if self.timeline is not None:
            # 强制将没有变化的物件以及所有后代物件也产生 detect_change 记录
            # 从而正确停用作用在根物件上的 GroupUpdater
            force_detect_items.union(self.walk_self_and_descendants())
            for item in force_detect_items:
                appr = self.timeline.item_appearances.get(item, None)
                if appr is None:
                    continue
                if not appr.stack.is_changed(item):
                    appr.stack.detect_change(item, self.timeline.current_time, force=True)

            # 如果设置了 auto_visible 且根物件是可见的
            # 那么 become 的最后会把所有子物件设为可见
            if auto_visible and self.timeline.is_visible(self):
                self.timeline.show(self)

        return self

    def store(self):
        copy_item = copy.copy(self)
        copy_item.reset_refresh()
        setattr(copy_item, SIGNAL_OBJ_SLOTS_NAME, None)

        copy_item._parents = []
        copy_item._children = []

        copy_item._stored = True
        copy_item._stored_parents = self.get_parents().copy()
        copy_item._stored_children = self.get_children().copy()

        self._copy_cmpts(self, copy_item)
        copy_item.init_connect()
        return copy_item

    def restore(self, other: Item) -> Self:
        if self._stored:
            self._stored_parents = other.get_parents().copy()
            self._stored_children = other.get_children().copy()

        for key in self.components.keys() & other.components.keys():
            self.components[key].become(other.components[key])

        return self

    def become_current(self) -> Self:
        """
        使用该方法可以中断动画过程，使物件立刻成为当前动画作用下的结果

        .. tip::

            物件本身是不会一直随着动画改变数据的

        在需要使用动画后的状态进行 ``.anim`` 等操作时较为实用
        """
        self.become(self.current(as_time=self.timeline.current_time))
        return self

    def _unstore(self, child_restorer: Callable[[Item], Item]) -> None:
        assert not self._children and self._stored_children is not None
        self._stored = False
        self.add(*[child_restorer(sub) for sub in self._stored_children])
        self.reset_refresh()

    @classmethod
    def align_for_interpolate(
        cls,
        item1: Item,
        item2: Item
    ) -> AlignedData[Self]:
        """
        进行数据对齐，以便插值
        """
        aligned = AlignedData(item1.store(),
                              item2.store(),
                              item1.store())

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
        aligned.data1._stored_children = resize_preserving_order(item1.get_children(), max_len)
        aligned.data2._stored_children = resize_preserving_order(item2.get_children(), max_len)

        return aligned

    def interpolate(
        self,
        item1: Item,
        item2: Item,
        alpha: float,
        *,
        path_func: PathFunc = straight_path,
    ) -> None:
        """
        进行插值（仅对该物件进行，不包含后代物件）
        """
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
        """
        固定在屏幕上，也就是即使摄像头移动位置也不会改变在屏幕上的位置
        """
        for item in self.walk_self_and_descendants(root_only):
            item._fix_in_frame = on
        return self

    def is_fix_in_frame(self) -> bool:
        return self._fix_in_frame

    def apply_depth_test(self, on: bool = True, *, root_only: bool = False) -> Self:
        for item in self.walk_self_and_descendants(root_only):
            item._depth_test = on
        return self

    def is_applied_depth_test(self) -> bool:
        return self._depth_test

    def apply_distance_sort(self, on: bool = True, *, root_only: bool = False) -> Self:
        for item in self.walk_self_and_descendants(root_only):
            item._distance_sort = on
        return self

    def is_applied_distance_sort(self) -> bool:
        return self._distance_sort

    # endregion

    # region state and target

    @dataclass
    class SavedState[T]:
        state: T
        root_only: bool

    def save_state(self, key: str = '', root_only: bool = False) -> Self:
        """
        保存物件状态，后续可使用 :meth:`load_state` 恢复，例如：

        .. code-block:: python

            item.save_state()

            # ...

            item.load_state()

        或者创建恢复动画：

        .. code-block:: python

            self.play(item.anim.load_state())

        例如可以用在，保存摄像机初始状态，在复杂的动画后恢复摄像机位置等场景中

        .. code-block:: python

            NumberPlane((-2, 2), (-2, 2), faded_line_ratio=1).show()

            self.camera.save_state()

            self.play(
                self.camera.anim.points.rotate(40 * DEGREES)
            )
            self.play(
                self.camera.anim.points.rotate(70 * DEGREES, axis=UP)
            )

            self.play(
                self.camera.anim.load_state()
            )
        """
        self._saved_states[key] = self.SavedState(self.store() if root_only else self.copy(), root_only)
        return self

    def load_state(self, key: str = '') -> Self:
        """
        恢复物件状态，详见 :meth:`save_state`
        """
        saved_state = self._saved_states[key]
        if saved_state.root_only:
            self.restore(saved_state.state)
        else:
            self.become(saved_state.state)
        return self

    def generate_target(self) -> Self:
        """
        拷贝生成一个 ``.target`` 物件，用于设置目标状态，最后使用 :class:`~.MoveToTarget` 创建过渡动画

        例如：

        .. code-block:: python

            txt = Text('A Matrix')
            mat = TypstMatrix([
                [1, 2, 3],
                [4, 5, 6],
                [7, 8, 9]
            ])

            self.play(Write(txt))

            Group(txt.generate_target(), mat).points.arrange(DOWN)

            self.play(
                MoveToTarget(txt),
                FadeIn(mat, UP)
            )
            self.forward()
        """
        self.target = self.copy()
        return self.target

    # endregion

    # region render

    def create_renderer(self) -> Renderer:
        return self.renderer_cls()

    def _mark_render_disabled(self) -> None:
        """
        由子类继承，用于标记 _render_disabled

        详见 :meth:`~.Timeline.render_all` 中的注释
        """
        pass

    # endregion

    # region timeline

    def show(self, root_only=False) -> Self:
        """
        显示物件
        """
        self.timeline.show(self, root_only=root_only)
        return self

    def hide(self, root_only=False) -> Self:
        """
        隐藏物件
        """
        self.timeline.hide(self, root_only=root_only)
        return self

    # endregion
