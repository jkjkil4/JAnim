from __future__ import annotations

import inspect
from contextvars import ContextVar
from typing import Callable

import janim.utils.refresh as refresh
from janim.typing import Self

FUNC_FOR_MANY_KEY = '__for_many'


class Component(refresh.Refreshable):
    def for_many[**P, R](func: Callable[P, R]) -> Callable[P, R]:
        # TODO: for_many 的注释
        func.__dict__[FUNC_FOR_MANY_KEY] = True
        return func

    class Binder:
        '''
        将组件与 :class:`janim.items.item.Item` 绑定

        例 | Example:

        .. code-block:: python

            class MyItem(Item):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)

                    with Component.Binder():
                        self.points = Cmpt_Points()
                        self.color = Cmpt_Rgbas()

        这样，``points`` 以及 ``color`` 就与 ``MyItem`` 的对象绑定了

        并且会得知是 ``MyItem`` 中创建的第几个组件，
        比如这里 points 是第 0 个，color 是第 1 个；
        这个序号，在 Item.broadcast_refresh_of_component 中使用到
        '''

        ctx_var: ContextVar[Component.Binder] = ContextVar('Component.Binder.ctx_var')

        def __init__(self, cls: type = None, obj: object = None):
            if (cls is None) != (obj is None):
                # TODO: i18n
                raise KeyError('`cls` 与 `obj` 必须同时被设置或缺省')

            if cls is None:
                f_back = inspect.currentframe().f_back

                if '__class__' not in f_back.f_locals:
                    # TODO: i18n
                    raise KeyError('`cls` 与 `obj` 缺省时必须在对象的方法中调用')

                self_arg_name = inspect.getargs(f_back.f_code).args[0]

                cls = f_back.f_locals['__class__']
                obj = f_back.f_locals[self_arg_name]

            from janim.items.item import Item
            self.cls = cls
            self.item: Item = obj

        def append(self, component: Component) -> int:
            '''
            在 ``Component`` 的 ``__init__`` 中被调用，
            用于得知是物件中创建的第几个组件
            '''
            idx = len(self.item.components)
            self.item.components.append(component)
            return idx

        def __enter__(self):
            self.token = self.ctx_var.set(self)

        def __exit__(self, exc_type, exc_value, exc_traceback):
            self.ctx_var.reset(self.token)

    def __init__(self, *args, get=False, apply=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.can_get = get
        self.can_apply = apply

        self.bind = Component.Binder.ctx_var.get(None)
        if self.bind is not None:
            self.bind_idx = self.bind.append(self)

    def mark_refresh(self, func: Callable | str, *, recurse_up=False, recurse_down=False) -> Self:
        super().mark_refresh(func)

        if self.bind is not None:
            self.bind.item.broadcast_refresh_of_component(
                self,
                func,
                recurse_up=recurse_up,
                recurse_down=recurse_down
            )
