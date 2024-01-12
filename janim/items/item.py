from __future__ import annotations

import functools
from typing import Callable, Self

from janim.items.relation import Relation
from janim.components.component import Component, CmptInfo
from janim.components.points import Cmpt_Points
from janim.typing import Vect

CLS_CMPTINFO_NAME = '__cls_cmptinfo'
OBJ_COMPONENTS_NAME = '__obj_components'


class _ItemMeta(type):
    '''
    作为 metaclass 记录定义在类中的所有 CmptInfo
    '''
    def __new__(cls, name: str, bases: tuple[type, ...], attrdict: dict):
        # 记录所有定义在类中的 CmptInfo
        cls_components: dict[str, Component] = {
            key: val
            for key, val in attrdict.items()
            if isinstance(val, CmptInfo)
        }

        attrdict[CLS_CMPTINFO_NAME] = cls_components

        return super().__new__(cls, name, bases, attrdict)


class Item(Relation['Item'], metaclass=_ItemMeta):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._init_components()

    def _init_components(self) -> None:
        '''
        创建出 CmptInfo 对应的 Component，
        并以同名存于对象中，起到在名称上覆盖类中的 CmptInfo 的效果

        因为 CmptInfo 的 __get__ 标注的返回类型是对应的 Component，
        所以以上做法没有影响基于类型标注的代码补全
        '''
        for cls in reversed(self.__class__.mro()):
            for key, info in cls.__dict__.get(CLS_CMPTINFO_NAME, {}).items():
                obj: Component = info.cls(*info.args, **info.kwargs)
                obj.set_bind_info(Component.BindInfo(cls, self, key))
                self.__dict__[key] = obj

    def broadcast_refresh_of_component(
        self,
        cmpt: Component,
        func: Callable | str,
        *,
        recurse_up=False,
        recurse_down=False
    ) -> Self:
        '''
        为 :meth:`~.Component.mark_refresh()`
        进行 ``recurse_up/down`` 的处理
        '''
        def mark(item: Item):
            item_component: Component = getattr(item, cmpt.bind_info.key)
            item_component.mark_refresh(func)

        if recurse_up:
            for item in self.walk_ancestors(cmpt.bind_info.decl_cls):
                mark(item)

        if recurse_down:
            for item in self.walk_descendants(cmpt.bind_info.decl_cls):
                mark(item)

    def astype[T](self, cls: type[T]) -> T:
        '''
        使得可以调用当前物件中没有的组件方法（前提是有被 ``@as_able`` 修饰）

        例 | Example:

        .. code-block:: python

            group = Group(
                Points(UP, RIGHT)
                Points(LEFT)
            )

        在这个例子中，``group`` 并不能 ``group.points.get_all()`` 来获取子物件中的所有点，
        但是可以使用 ``group.astype(Points).points.get_all()`` 来做到
        '''
        return self._As(self, cls)

    class _As:
        '''
        astype(...) 得到的伪造物件对象，接上 ``.cmpt_name`` 得到伪造组件 ``_TakedCmpt`` 的对象
        '''
        def __init__(self, origin: Item, cls: type):
            assert issubclass(cls, Item)

            self.origin = origin
            self.cls = cls

        def __getattr__(self, name: str):
            try:
                attr = getattr(self.cls, name)
                if not isinstance(attr, CmptInfo):
                    raise AttributeError()

            except AttributeError:
                # TODO: i18n
                raise AttributeError(f"'{self.cls.__name__}' 没有叫作 '{name}' 的组件")

            return self._TakedCmpt(self, name, attr)

        class _TakedCmpt:
            '''
            astype(...).cmpt_name 得到的伪造组件对象
            '''
            def __init__(self, item_as: Item._As, cmpt_name: str, cmpt_info: CmptInfo):
                self.item_as = item_as
                self.cmpt_name = cmpt_name
                self.cmpt_info = cmpt_info

            def __getattr__(self, name: str):
                try:
                    attr = getattr(self.cmpt_info.cls, name)
                    if not callable(attr) or not Component.is_as_able(attr):
                        raise AttributeError()

                except AttributeError:
                    # TODO: i18n
                    raise AttributeError(f"{self.cmpt_info.cls.__name__} 没有叫作 '{name}' 的 as_able 方法")

                return functools.partial(attr, self)


class Group(Item):
    '''
    将物件组成一组
    '''
    def __init__(self, *objs, **kwargs):
        super().__init__(**kwargs)
        self.add(*objs)
