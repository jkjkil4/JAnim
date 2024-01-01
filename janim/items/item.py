from __future__ import annotations

import copy
import enum
import inspect
import itertools as it
import sys
from functools import wraps, update_wrapper
from typing import Any, Callable, Iterable, TypeVar, Generator, Type

import numpy as np

from janim.constants import (DEFAULT_ITEM_TO_EDGE_BUFF,
                             DEFAULT_ITEM_TO_ITEM_BUFF, DOWN, IN, LEFT,
                             MED_SMALL_BUFF, ORIGIN, OUT, PI, RIGHT, UP)
from janim.logger import log
from janim.typing import Self, Vect, VectArray
from janim.utils.space_ops import angle_of_vector, get_norm, rotation_matrix
from janim.utils.unique_nparray import UniqueNparray


ItemBaseT = TypeVar('ItemBaseT', bound='ItemBase')


class ItemBase:
    '''
    物件的基类，定义了物件结构关系，以及一些有用的封装

    The base class for items, defining the structural
    relationships of items and providing some useful encapsulation.

    继承 ItemBase 及有关类时，应完成对 copy 的继承，使得子类的数据能被正常复制

    When inheriting from ItemBase or related classes,
    you should implement inheritance for copy to ensure
    that the data of the subclass can be copied correctly.

    .. code-block:: python

        def copy(self) -> Self:
            copy_item = super().copy()

            # ===========
            # 有关数据复制
            # Data copying
            # ===========

            return copy_item
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.parents: list[ItemBase] = []
        self.subitems: list[ItemBase] = []

        self.refresh_required: dict[str, bool] = {}
        self.refresh_stored_data: dict[str, Any] = {}

    class SelfSignal:
        '''
        一般用于在 ``func`` 造成影响后，需要对其它数据进行更新时进行响应

        当 ``func`` 被该类修饰，使用 ``Class.func.emit(self)`` 后

        - 会调用所有被 ``func.slots()`` 修饰的方法
        - 会为所有被 ``func.refresh()`` 修饰的方法调用 ``mark_refresh_required``
        - 可以在上述方法中传入 ``key`` 参数以区分调用
        - ``func.refresh()`` 除了 ``key`` 之外，还可以传入 ``recurse_down/up``
        - ``emit`` 方法可以传入额外的参数给被调用的 ``slots``

        注意：
        被 ``func.slot()`` 或 ``func.refresh()`` 修饰的方法需要与 ``func`` 在同一个类或者其子类中

        =====

        Generally used to respond to updates in other data after an impact caused by ``func``.

        When a method ``func`` is decorated with this class and used as ``Class.func.emit(self)``:

        - It will invoke all methods decorated with ``func.slots()``.
        - It will call ``mark_refresh_required`` for all methods decorated with ``func.refresh()``.
        - You can pass a ``key`` parameter in the above methods to distinguish the calls.
        - Besides ``key``, ``func.refresh()`` can also take ``recurse_down/up`` as parameters.
        - The ``emit`` method can pass additional arguments to the invoked ``slots``.

        Note:
        Methods decorated with ``func.slot()`` or ``func.refresh()`` need to be in the same class or its subclass.

        =====

        例 | Example:

        .. code-block:: python

            class User(ItemBase):
                def __init__(self, name: str):
                    super().__init__()
                    self.name = name
                    self.msg = ''

                @ItemBase.SelfSignal
                def set_msg(self, msg: str) -> None:
                    self.msg = msg
                    User.set_msg.emit(self)

                @set_msg.slot()
                def notifier(self) -> None:
                    print("User's message changed")

                @set_msg.refresh()
                @ItemBase.register_refresh_required
                def get_test(self) -> str:
                    return f'[{self.name}] {self.msg}'

            user = User('jkjkil')
            user.set_msg('hello')   # Output: User's message changed
            print(user.get_text())  # Output: [jkjkil] hello

        还可以参考 | See also：

        - :meth:``janim.items.item.Item.get_points()``
        - ``test.items.item_test.ItemBaseTest.test_signal_with_inherit()``
        '''
        def __init__(self, func: Callable):
            self.func = func
            update_wrapper(self, func)

            Key = FullQualname = str
            Slots = list[Callable]
            RefreshSlots = list[Callable, bool, bool]

            self.slots: dict[
                Key,
                dict[
                    FullQualname,
                    tuple[
                        Slots,
                        RefreshSlots
                    ]
                ]
            ] = {}

        def __get__(self, instance, owner):
            return self if instance is None else self.func.__get__(instance, owner)

        @staticmethod
        def get_cls_full_qualname_from_fback() -> str:
            cls_locals = inspect.currentframe().f_back.f_back.f_locals
            module = cls_locals['__module__']
            qualname = cls_locals['__qualname__']
            return f'{module}.{qualname}'

        @staticmethod
        def get_cls_full_qualname(cls: type) -> str:
            return f'{cls.__module__}.{cls.__qualname__}'

        def ensure_slots_list_available(self, key: str, full_qualname: str) -> None:
            if key not in self.slots:
                self.slots[key] = {full_qualname: ([], [])}

            elif full_qualname not in self.slots[key]:
                self.slots[key][full_qualname] = ([], [])

        def slot(self, *, key: str = ''):
            '''
            被该修饰器所修饰的方法会在 ``SelfSignal`` 触发时被调用

            A method decorated with this decorator will be called when a ``SelfSignal`` is triggered.
            '''
            def decorator(func):
                full_qualname = self.get_cls_full_qualname_from_fback()
                self.ensure_slots_list_available(key, full_qualname)
                self.slots[key][full_qualname][0].append(func)

                return func

            return decorator

        def refresh(self, *, recurse_down: bool = False, recurse_up: bool = False, key: str = ''):
            '''
            被该修饰器所修饰的方法会在 ``SelfSignal`` 触发时，标记 ``refresh_required``

            A method decorated with this decorator will mark ``refresh_required`` when a ``SelfSignal`` is triggered.
            '''
            def decorator(func):
                full_qualname = self.get_cls_full_qualname_from_fback()
                self.ensure_slots_list_available(key, full_qualname)
                self.slots[key][full_qualname][1].append((func, recurse_down, recurse_up))

                return func

            return decorator

        def emit(self, item: ItemBase, *args, key: str = '', **kwargs):
            '''触发 ``SelfSignal`` | Trigger ``SelfSignal``'''
            try:
                all_slots = self.slots[key]
            except KeyError:
                return

            for cls in item.__class__.mro():
                try:
                    slots, refresh_slots = all_slots[self.get_cls_full_qualname(cls)]
                except KeyError:
                    continue

                for func in slots:
                    func(item, *args, **kwargs)

                for func, recurse_down, recurse_up in refresh_slots:
                    item.mark_refresh_required(func, recurse_down=recurse_down, recurse_up=recurse_up)

    class Signal:
        '''
        用于触发信号后让其它方法能被一同调用

        当 ``func`` 被该类修饰，使用 ``self.func.emit()`` 后：

        - 会调用所有通过 ``func.connect(...)`` 绑定的方法
        - 可以在 ``emit`` 或 ``connect`` 方法中传入 ``key`` 参数以区分调用
        - ``emit`` 方法可以传入额外的参数给被调用的 ``slots``

        ===

        Used to trigger a signal and allow other methods to be called together.

        When ``func`` is decorated with this class, after using ``self.func.emit()``:

        - It will call all methods bound through ``func.connect(...)``.
        - You can pass a ``key`` parameter in the ``emit`` or ``connect`` methods to differentiate the calls.
        - The ``emit`` method can pass additional parameters to the called ``slots``.
        '''  # TODO: Example for Signal
        class __BindSignal:
            def __init__(self, signal: ItemBase.Signal, instance, owner):
                self.signal = signal
                self.instance = instance
                self.owner = owner

            def __call__(self, *args, **kwargs):
                return self.signal.func(self.instance, *args, **kwargs)

            def connect(self, slot: Callable, *, key: str = '') -> None:
                self.signal.connect(self.instance, slot, key=key)

            def emit(self, *args, key: str = '', **kwargs) -> None:
                self.signal.emit(self.instance, *args, key=key, **kwargs)

        def __init__(self, func: Callable):
            self.func = func
            update_wrapper(self, func)

            self.slots: dict[int, dict[str, list[Callable]]] = {}

        def __call__(self, *args, **kwargs):
            return self.func(*args, **kwargs)

        def __get__(self, instance, owner):
            return self if instance is None else ItemBase.Signal.__BindSignal(self, instance, owner)

        def ensure_slots_list_available(self, signal_obj_id: int, key: str) -> None:
            if signal_obj_id not in self.slots:
                self.slots[signal_obj_id] = {key: []}

            elif key not in self.slots[signal_obj_id]:
                self.slots[signal_obj_id][key] = []

        def connect(self, signal_obj, slot: Callable, *, key: str = '') -> None:
            signal_obj_id = id(signal_obj)
            self.ensure_slots_list_available(signal_obj_id, key)
            self.slots[signal_obj_id][key].append(slot)

        def emit(self, signal_obj, *args, key: str = '', **kwargs) -> None:
            try:
                slots = self.slots[id(signal_obj)][key]
            except KeyError:
                return

            for slot in slots:
                slot(*args, **kwargs)

    # region refreshing

    def register_refresh_required(func: Callable) -> Callable:
        '''
        refresh 相关方法
        用于在需要时才进行值的重新计算，提升性能

        当一个方法 self.func 被 ``register_refresh_required`` 修饰后
        会记忆 self.func 被调用后的返回值，并在之后的调用中直接返回该值，而不对 self.func 进行真正的调用
        需要 ``mark_refresh_required(self.func)`` 才会对 self.func 重新调用以更新返回值

        例如，``get_family`` 方法不会每次都进行计算
        只有在 ``add`` 或 ``remove`` 执行后，才会将 ``get_family`` 标记为需要更新
        使得在下次调用 ``get_family`` 才重新计算结果并返回

        可参考 ``test.items.item_test.ItemTest.test_refresh_required()``

        =====

        Methods related to refreshing
        Used to recalculate values only when necessary for performance improvement

        When a method self.func is decorated with ``register_refresh_required``,
        it memorizes the return value of self.func and directly returns that value in subsequent calls,
        without actually calling self.func.
        ``mark_refresh_required(self.func)`` is needed to trigger a reevaluation
        of self.func and update the return value.

        For example, the ``get_family`` method does not recalculate every time.
        It is only marked for update after ``add`` or ``remove`` is executed,
        making it recalculated and returning the result the next time ``get_family`` is called.

        See ``test.items.item_test.ItemTest.test_refresh_required()`` for an example.
        '''
        name = func.__name__

        @wraps(func)
        def wrapper(self: ItemBase, *args, **kwargs):
            try:
                is_required = self.refresh_required[name]
            except KeyError:
                is_required = True

            if is_required:
                ret = self.refresh_stored_data[name] = func(self, *args, **kwargs)
                self.refresh_required[name] = False
                return ret
            return self.refresh_stored_data[name]

        return wrapper

    def mark_refresh_required(self, func: Callable, *, recurse_down: bool = False, recurse_up: bool = False) -> Self:
        '''
        标记指定的 ``func`` 需要进行更新

        ``recurse_down``: 是否递归调用子物件的该方法
        ``recurse_up``: 是否递归调用父物件的该方法

        =====

        Marks the specified ``func`` for an update.

        ``recurse_down``: Whether to recursively call the method on subitems.
        ``recurse_up``: Whether to recursively call the method on parents.
        '''
        self.refresh_required[func.__name__] = True
        if recurse_down:
            for item in self.subitems:
                item.mark_refresh_required(func, recurse_down=True)
        if recurse_up:
            for item in self.parents:
                item.mark_refresh_required(func, recurse_up=True)

    # endregion

    # region relation

    '''
    两个物件之间可以建立 parent-subitem 双向关系
    主要用于 mark_refresh_required 以及一些属性的传递
    并不与渲染顺序直接相关

    Bidirectional parent-subitem relationship can be established between two items.
    Mainly used for ``mark_refresh_required`` and the transfer of some properties.
    It is not directly related to the rendering order.
    '''

    @SelfSignal
    def subitems_changed(self) -> None:
        ItemBase.subitems_changed.emit(self)

    def add(self, *items: ItemBase) -> Self:
        '''
        向该物件添加子物件

        Add subitems to this item.
        '''
        for item in items:
            # 理论上这里判断 item not in self.subitems 就够了
            # 但是防止有被私自修改 self.parents 以及 self.subitems 的可能
            # 所以这里都判断了
            if item not in self.subitems:
                self.subitems.append(item)
            if self not in item.parents:
                item.parents.append(self)

        self.subitems_changed()
        return self

    def remove(self, *items: ItemBase) -> Self:
        '''
        从该物件移除子物件

        Remove subitems from this item.
        '''
        for item in items:
            # 理论上这里判断 item in self.subitems 就够了
            # 原因同 add
            try:
                self.subitems.remove(item)
            except ValueError: ...
            try:
                item.parents.remove(self)
            except ValueError: ...

        self.subitems_changed()
        return self

    @subitems_changed.refresh(recurse_up=True)
    @register_refresh_required
    def get_family(self) -> list[ItemBase]:
        '''
        获取该物件的所有子物件，即包括自己和子物件的子物件

        Get all subitems of this item, including itself and the subitems of its subitems.
        '''
        return [self, *it.chain(*[item.get_family() for item in self.subitems])]

    def walk_nearest_subitems(self, base_cls: Type[ItemBaseT]) -> Generator[ItemBaseT, None, None]:
        for subitem in self.subitems:
            if isinstance(subitem, base_cls):
                yield subitem
            else:
                for item in subitem.walk_nearest_subitems(base_cls):
                    yield item

    def __getitem__(self, value) -> Self:   # 假装返回 Self，用于类型提示
        if isinstance(value, slice):
            return GroupClass(*self.subitems[value])
        return self.subitems[value]

    def __iter__(self):
        return iter(self.subitems)

    def __len__(self):
        return len(self.subitems)

    # endregion

    # region 快速操作 | quick operations

    @property
    def for_all(self) -> Self:  # 假装返回 Self，方便代码补全
        '''
        对自己 ``get_family()`` 的所有子物件进行操作

        Operates on all items obtained from ``get_family()``.
        '''
        return BatchOp(*self.get_family())

    def for_all_p(self, **kwargs) -> Self:
        '''
        同 ``for_all``，但是可以传入额外参数

        Same as for_all, but can accept additional parameters.
        '''
        return BatchOp(*self.get_family(), **kwargs)

    @property
    def for_all_except_self(self) -> Self:
        '''
        对不包括自己的 ``get_family()`` 的所有子物件进行操作

        Operatres on all items obtained from ``get_family()``, excluding the item itself.
        '''
        return BatchOp(*self.get_family()[1:])

    def for_all_except_self_p(self, **kwargs) -> Self:
        '''
        同 ``for_all_except_self``，但是可以传入额外参数

        Same as ``for_all_except_self``, but can accept additional parameters.
        '''
        return BatchOp(*self.get_family()[1:], **kwargs)

    @property
    def for_sub(self) -> Self:
        '''
        对 ``subitems`` 中的物件进行操作

        Operates on subitems.
        '''
        return BatchOp(*self.subitems)

    def for_sub_p(self, **kwargs) -> Self:
        '''
        同 ``for_sub``，但是可以传入额外参数

        Same as ``for_sub``, but can accept additional parameters.
        '''
        return BatchOp(*self.subitems, **kwargs)

    # endregion

    # region 数据复制 | data copying

    def copy(self) -> Self:
        '''
        拷贝数据以及子物件，产生一样的另一个物件

        Copy data and sub-items to create an identical object.
        '''

        copy_item = copy.copy(self)

        # relation
        copy_item.parents = []
        copy_item.subitems = []
        copy_item.add(*[m.copy() for m in self])

        # 清空，使得所有操作都要重新计算数据
        # Clear, so that all opeartions require recalculating data.
        self.refresh_required.clear()

        # 既然 refresh_required 清空了，那么这个就顺便也清空吧，反正也要重新计算的
        # Since refresh_required is cleared, clear this too, as it needs to be recalculated.
        self.refresh_stored_data.clear()

        return copy_item

    def __mul__(self, times: int) -> Self:  # 假装返回 Self，方便代码补全 | Pretends to return Self for code completion.
        '''
        将自身复制 ``times`` 次，组合到一个 ``Group`` 中

        Duplicate itself ``times`` times and group them into a new ``Group``.
        '''
        return GroupClass(
            *(self.copy() for _ in range(times))
        )

    # endregion


class Item(ItemBase):
    '''
    物件

    - 定义了 点坐标序列、边界框
    - 实现了 坐标变换、位移 等操作

    =====

    Item

    - Defines point coordinates sequence and bounding box.
    - Implements coordinate transformations, shifts, and other operations.
    '''

    def __init__(
        self,
        *args,
        points: VectArray = np.array([]),
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.points = UniqueNparray()
        self.set_points(points)

        # TODO: self.markers

    def copy(self) -> Self:
        copy_item = super().copy()

        copy_item.points = UniqueNparray()
        copy_item.points.data = self.points.data

        # TODO: copy: markers

    # region points

    def get_points(self) -> np.ndarray:
        return self.points.data

    def get_all_points(self) -> np.ndarray:
        '''
        得到所有点，也就是包括 ``get_family()`` 里所有物件的

        Get all points, including those of all sub-items.
        '''
        return np.vstack(self.for_all.get_points())

    @ItemBase.SelfSignal
    def set_points(self, points: VectArray) -> Self:
        '''
        设置点坐标数据，每个坐标点都有三个分量

        使用形如 ``set_points([[1.5, 3, 2], [2, 1.5, 0]])`` 的形式

        Set point coordinate data, with each point having three components.

        Use a format like ``set_points([[1.5, 3, 2], [2, 1.5, 0]])``.
        '''
        if not isinstance(points, np.ndarray):
            points = np.array(points)
        if points.size == 0:
            points = np.zeros((0, 3))

        assert points.ndim == 2
        assert points.shape[1] == 3

        cnt_changed = len(points) != len(self.points.data)

        self.points.data = points

        if cnt_changed:
            Item.set_points.emit(self, key='count')
        Item.set_points.emit(self)

        return self

    def clear_points(self) -> Self:
        self.set_points(np.zeros((0, 3)))
        return self

    def append_points(self, points: VectArray) -> Self:
        '''
        追加点坐标数据，每个坐标点都有三个分量

        使用形如 ``append_points([[1.5, 3, 2], [2, 1.5, 0]])`` 的形式

        Append point coordinate data, with each point having three components.

        Use a format like ``append_points([[1.5, 3, 2], [2, 1.5, 0]])``.
        '''
        self.set_points(np.vstack([
            self.get_points(),
            points
        ]))
        return self

    @ItemBase.SelfSignal
    def reverse_points(self) -> Self:
        '''使点倒序 | reverse the order of points'''
        self.set_points(self.get_points()[::-1])
        Item.reverse_points.emit(self)
        return self

    # TODO: resize_points

    def points_count(self) -> int:
        return len(self.get_points())

    def has_points(self) -> bool:
        return self.points_count() > 0

    def get_start(self) -> np.ndarray:
        '''
        得到 ``points`` 的第一个点 | Obtains the first point of ``points``.
        '''
        self.throw_error_if_no_points()
        return self.get_points()[0].copy()

    def get_end(self) -> np.ndarray:
        '''
        得到 ``points`` 的最后一个点 | Obtains the last point of ``points``.
        '''
        self.throw_error_if_no_points()
        return self.get_points()[-1].copy()

    def throw_error_if_no_points(self) -> None:
        if not self.has_points():
            # TODO: i18n
            message = "Cannot call Item.{} " +\
                      "for a Item with no points"
            caller_name = sys._getframe(1).f_code.co_name
            raise Exception(message.format(caller_name))

    # endregion

    # region 边界箱 | bounding_box

    class BoundingBox:
        '''
        边界框，``self.data`` 包含三个元素，分别为左下，中心，右上

        Bounding box, ``self.data`` includes three elements representing the bottom-left, center, and top-right.
        '''
        def __init__(self, points: VectArray):
            self.data = self.compute(points)

        @staticmethod
        def compute(points: VectArray) -> np.ndarray:
            points = np.array(points)

            if len(points) == 0:
                return np.zeros((3, 3))

            mins = points.min(0)
            maxs = points.max(0)
            mids = (mins + maxs) / 2

            return np.array([mins, mids, maxs])

        def get(self, direction: Vect) -> np.ndarray:
            '''
            获取边界框边上的坐标

            例如：

            - 传入 UR，则返回边界框右上角的坐标
            - 传入 RIGHT，则返回边界框右侧中心的坐标

            =====

            Obtains the coordinates on the borders of the bounding box.

            Examples:

            - If UR is passed, it returns the coordinates of the upper-right corner of the bounding box.
            - If RIGHT is passed, it returns the coordinates of the center on the right side of the bounding box.
            '''
            indices = (np.sign(direction) + 1).astype(int)
            return np.array([
                self.data[indices[i]][i]
                for i in range(3)
            ])

        def get_continuous(self, direction: Vect) -> np.ndarray:
            # TODO: 完善 `get_continuous` 注释
            dl, center, ur = self.data
            corner_vect = (ur - center)
            return center + direction / np.max(np.abs(np.true_divide(
                direction, corner_vect,
                out=np.zeros(len(direction)),
                where=((corner_vect) != 0)
            )))

        @property
        def top(self) -> np.ndarray:
            return self.get(UP)

        @property
        def bottom(self) -> np.ndarray:
            return self.get(DOWN)

        @property
        def right(self) -> np.ndarray:
            return self.get(RIGHT)

        @property
        def left(self) -> np.ndarray:
            return self.get(LEFT)

        @property
        def zenith(self) -> np.ndarray:
            return self.get(OUT)

        @property
        def nadir(self) -> np.ndarray:
            return self.get(IN)

        @property
        def center(self) -> np.ndarray:
            return self.data[1]

        def length_over_dim(self, dim: int) -> float:
            return abs((self.data[2] - self.data[0])[dim])

        @property
        def width(self) -> float:
            return self.length_over_dim(0)

        @property
        def height(self) -> float:
            return self.length_over_dim(1)

        @property
        def depth(self) -> float:
            return self.length_over_dim(2)

        def coord(self, dim: int, direction=ORIGIN) -> float:
            return self.get(direction)[dim]

        @property
        def x(self, direction=ORIGIN) -> float:
            return self.coord(0, direction)

        @property
        def y(self, direction=ORIGIN) -> float:
            return self.coord(1, direction)

        @property
        def z(self, direction=ORIGIN) -> float:
            return self.coord(2, direction)

    @property
    @set_points.refresh()
    @ItemBase.register_refresh_required
    def self_box(self) -> BoundingBox:
        '''
        同 ``box``，但仅表示自己 ``points`` 的包围框，不考虑子物件的

        Same as ``box``, but only represents the bounding box of its own ``points``, excluding sub-items.
        '''
        return Item.BoundingBox(self.get_points())

    @property
    @set_points.refresh(recurse_up=True)
    @ItemBase.subitems_changed.refresh(recurse_up=True)
    @ItemBase.register_refresh_required
    def box(self) -> BoundingBox:
        '''
        表示物件（包括子物件）的矩形包围框

        Rectangular bounding box of the item (including child items).
        '''
        all_points = np.vstack([
            self.self_box.data,
            *[item.box.data for item in self.walk_nearest_subitems(Item)]
        ])
        return Item.BoundingBox(all_points)

    # endregion

    # region 变换 | Transform

    def apply_points_function(
        self,
        func: Callable[[np.ndarray], Vect],
        about_point: Vect | None = None,
        about_edge: Vect = ORIGIN,
        for_all: bool = False
    ) -> Self:
        '''
        视 ``about_point`` 为原点，若其为 ``None``，则将物件在 ``about_edge`` 方向上的边界作为 ``about_point``

        注意：

        如果有传入 ``about_point``，则以下二者调用后的效果没有区别：

        - ``.for_all.apply_points_function(...)``
        - ``.apply_points_function(..., for_all=True)``

        如果没有传入 ``about_point``，而是以 ``about_edge`` 确定变换原点：

        - 那么 ``.for_all.apply_points_function(...)`` 会以每个子物件的边界框分别确定 ``about_point`` 进行变换
        - 而 ``.apply_points_function(..., for_all=True)`` 会以全体的边界框确定共同的 ``about_point`` 进行变换

        =====

        Apply a function to the points of the object, considering a specified reference point or edge.

        If ``about_point`` is provided, it is considered as the origin for the transformation.
        If ``about_point`` is ``None``, the edge in the ``about_edge`` direction is used as the reference point.

        Note:

        If ``about_point`` is provided, the following two calls have the same effect:

        - ``.for_all.apply_points_function(...)``
        - ``.apply_points_function(..., for_all=True)``

        If ``about_point`` is not provided, and the transformation origin is determined by ``about_edge``:

        - ``.for_all.apply_points_function(...)`` will use the border
        of each sub-item to determine ``about_point`` individually.
        - ``.apply_points_function(..., for_all=True)`` will use the combined border
        of all items to determine a common ``about_point`` for the transformation.
        '''
        if about_point is None and about_edge is not None:
            if for_all:
                about_point = self.box.get(about_edge)
            else:
                about_point = self.self_box.get(about_edge)

        def apply(item: Item):
            if not item.has_points():
                return

            if about_point is None:
                item.set_points(func(item.get_points()))
            else:
                item.set_points(func(item.get_points() - about_point) + about_point)

        if for_all:
            for item in self.get_family():
                apply(item)
        else:
            apply(self)

        return self

    def apply_function(
        self,
        function: Callable[[np.ndarray], np.ndarray],
        about_point: Vect = ORIGIN,
        **kwargs
    ) -> Self:
        '''
        以每个点为单位进行变换；以默认的原点作用变换，而不是物件的中心

        Apply a transformation to each point individually.
        Default to applying the transformation about the origin, not items center.
        '''
        self.apply_points_function(
            lambda points: np.array([function(p) for p in points]),
            about_point=about_point,
            **kwargs
        )
        return self

    def apply_matrix(
        self,
        matrix: VectArray,
        about_point: Vect | None = None,
        about_edge: Vect | None = None,
        **kwargs
    ) -> Self:
        '''
        将矩阵变换作用于 ``points``；以默认的原点作用变换，而不是物件的中心

        Apply a matrix transformation to the ``points``.
        Default to applying the transformation about the origin, not items center.
        '''
        if about_point is None and about_edge is None:
            about_point = ORIGIN
        full_matrix = np.identity(3)
        matrix = np.array(matrix)
        full_matrix[:matrix.shape[0], :matrix.shape[1]] = matrix
        self.apply_points_function(
            lambda points: np.dot(points, full_matrix.T),
            about_point=about_point,
            about_edge=about_edge,
            **kwargs
        )
        return self

    def apply_complex_function(self, function: Callable[[complex], complex], **kwargs) -> Self:
        '''
        将复变函数作用于 ``points``

        Apply a complex-valued function to the ``points``.
        '''  # TODO: 明确是作用于原点还是物件中心
        def R3_func(point):
            x, y, z = point
            xy_complex = function(complex(x, y))
            return [
                xy_complex.real,
                xy_complex.imag,
                z
            ]
        return self.apply_function(R3_func, **kwargs)

    def rotate(
        self,
        angle: float,
        axis: Vect = OUT,
        about_point: Vect | None = None,
        **kwargs
    ) -> Self:
        '''
        以 ``axis`` 为方向，``angle`` 为角度旋转，可传入 ``about_point`` 指定相对于以哪个点为中心

        Rotate the item by an ``angle`` around the specified ``axis``,
        with an optional ``about_point`` about which the rotation should be performed.
        '''
        rot_matrix_T = rotation_matrix(angle, axis).T
        self.apply_points_function(
            lambda points: np.dot(points, rot_matrix_T),
            about_point,
            **kwargs
        )
        return self

    def flip(self, axis: Vect = UP, **kwargs) -> Self:
        '''
        绕 axis 轴翻转

        Flip the item around the specified axis.
        '''
        self.rotate(PI, axis, **kwargs)
        return self

    def scale(
        self,
        scale_factor: float | Iterable,
        min_scale_factor: float = 1e-8,
        about_point: Vect | None = None,
        about_edge: Vect = ORIGIN
    ) -> Self:
        '''
        将物件缩放指定倍数

        如果传入的倍数是可遍历的对象，那么则将其中的各个元素作为坐标各分量缩放的倍数，
        例如传入 ``scale_factor`` 为 ``(2, 0.5, 1)`` 则是在 ``x`` 方向上缩放为两倍，在 ``y`` 方向上压缩为原来的一半，在 ``z`` 方向上保持不变

        =====

        Scale the item by a specified factor.

        If the scale factor provided is an iterable object, each element
        will be used as the scaling factor for the corresponding coordinate component.

        For example, if ``scale_factor`` is ``(2, 0.5, 1)``, the item will be scaled by a factor
        of 2 along the ``x`` axis, compressed by half along the ``y`` axis, and remain unchanged along the ``z`` axis.
        '''
        if isinstance(scale_factor, Iterable):
            scale_factor = np.array(scale_factor).clip(min=min_scale_factor)
        else:
            scale_factor = max(scale_factor, min_scale_factor)

        self.apply_points_function(
            lambda points: scale_factor * points,
            about_point=about_point,
            about_edge=about_edge
        )
        return self

    def stretch(self, factor: float, dim: int, **kwargs) -> Self:
        '''
        在指定的 ``dim`` 方向上使物件伸缩

        Stretch the object along the specified ``dim`` direction.
        '''
        def func(points):
            points[:, dim] *= factor
            return points
        self.apply_points_function(func, **kwargs)
        return self

    def rescale_to_fit(self, length: float, dim: int, stretch: bool = False, **kwargs) -> Self:
        old_length = self.box.length_over_dim(dim)
        if old_length == 0:
            return self
        if stretch:
            self.stretch(length / old_length, dim, **kwargs)
        else:
            self.scale(length / old_length, **kwargs)
        return self

    def set_width(self, width: float, stretch: bool = False, **kwargs) -> Self:
        '''
        如果 ``stretch`` 为 ``False``（默认），则表示等比缩放

        If ``stretch`` is ``False`` (default), it indicates proportional scaling.
        '''
        return self.rescale_to_fit(width, 0, stretch=stretch, **kwargs)

    def set_height(self, height: float, stretch: bool = False, **kwargs) -> Self:
        '''
        如果 ``stretch`` 为 ``False``（默认），则表示等比缩放

        If ``stretch`` is ``False`` (default), it indicates proportional scaling.
        '''
        return self.rescale_to_fit(height, 1, stretch=stretch, **kwargs)

    def set_depth(self, depth: float, stretch: bool = False, **kwargs) -> Self:
        '''
        如果 ``stretch`` 为 ``False``（默认），则表示等比缩放

        If ``stretch`` is ``False`` (default), it indicates proportional scaling.
        '''
        return self.rescale_to_fit(depth, 2, stretch=stretch, **kwargs)

    def set_size(
        self,
        width: float | None = None,
        height: float | None = None,
        depth: float | None = None,
        **kwargs
    ) -> Self:
        if width:
            self.set_width(width, True, **kwargs)
        if height:
            self.set_height(height, True, **kwargs)
        if depth:
            self.set_depth(depth, True, **kwargs)
        return self

    def replace(self, item: Item, dim_to_match: int = 0, stretch: bool = False) -> Self:
        '''
        放到和 item 的位置，并且大小相同

        Position the object at the same location and with the same size as the specified item.
        '''
        if not item.points_count() and not item.subitems:
            self.scale(0)
            return self
        if stretch:
            # If stretch is True, rescale each dimension to match the corresponding dimension of the item.
            for i in range(3):
                self.rescale_to_fit(item.box.length_over_dim(i), i, stretch=True)
        else:
            # If stretch is False, rescale only the dimension specified by dim_to_match to match the item.
            self.rescale_to_fit(
                item.box.length_over_dim(dim_to_match),
                dim_to_match,
                stretch=False
            )
        # Shift the object to the center of the specified item.
        self.shift(item.box.center - self.box.center)
        return self

    def surround(
        self,
        item: Item,
        dim_to_match: int = 0,
        stretch: bool = False,
        buff: float = MED_SMALL_BUFF
    ) -> Self:
        '''
        与 ``replace`` 类似，但是会向外留出 ``buff`` 间距

        Similar to ``replace`` but leaves a buffer space of ``buff`` around the item.
        '''
        self.replace(item, dim_to_match, stretch)
        length = item.box.length_over_dim(dim_to_match)
        self.scale((length + buff) / length)
        return self

    def put_start_and_end_on(self, start: Vect, end: Vect) -> Self:
        '''
        通过旋转和缩放，使得物件的起点和终点被置于 ``start`` 和 ``end``

        Rotate and scale this item such that its start and end points are positioned at ``start`` and ``end``.
        '''
        curr_start, curr_end = self.get_start(), self.get_end()
        curr_vect = curr_end - curr_start
        if np.all(curr_vect == 0):
            raise Exception("Cannot position endpoints of closed loop")
        target_vect = end - start
        self.scale(
            get_norm(target_vect) / get_norm(curr_vect),
            about_point=curr_start,
        )
        self.rotate(
            angle_of_vector(target_vect) - angle_of_vector(curr_vect),
        )
        self.rotate(
            np.arctan2(curr_vect[2], get_norm(curr_vect[:2])) - np.arctan2(target_vect[2], get_norm(target_vect[:2])),
            axis=np.array([-target_vect[1], target_vect[0], 0]),
        )
        self.shift(start - self.get_start())
        return self

    # endregion

    # region 位移 | movement

    def shift(self, vector: Vect) -> Self:
        '''
        相对移动 ``vector`` 向量

        Shift the object by the specified ``vector``.
        '''
        self.apply_points_function(
            lambda points: points + vector,
            about_edge=None
        )
        return self

    def move_to(
        self,
        target: Item | Vect,
        aligned_edge: Vect = ORIGIN,
        coor_mask: Iterable = (1, 1, 1)
    ) -> Self:
        '''
        移动到 ``target`` 的位置

        Move this item to the position of ``target``.
        '''
        if isinstance(target, Item):
            target = target.box.get(aligned_edge)
        point_to_align = self.box.get(aligned_edge)
        self.shift((target - point_to_align) * coor_mask)
        return self

    def align_to(
        self,
        item_or_point: Item | Vect,
        direction: Vect = ORIGIN
    ) -> Self:
        """
        Examples:
        item1.align_to(item2, UP) moves item1 vertically so that its
        top edge lines ups with item2's top edge.

        item1.align_to(item2, direction = RIGHT) moves item1
        horizontally so that it's center is directly above/below
        the center of item2
        """  # TODO: 完善 align_to 注释
        if isinstance(item_or_point, Item):
            point = item_or_point.box.get(direction)
        else:
            point = item_or_point

        for dim in range(3):
            if direction[dim] != 0:
                self.set_coord(point[dim], dim, direction)

        return self

    def to_center(self) -> Self:
        '''
        移动到原点 ``(0, 0, 0)``

        Move this item to the origin ``(0, 0, 0)``.
        '''
        self.shift(-self.box.center)
        return self

    # TODO: def to_border(
    #     self,
    #     direction: Vect,
    #     buff: float = DEFAULT_ITEM_TO_EDGE_BUFF
    # ) -> Self:
    #     """
    #     Direction just needs to be a vector pointing towards side or
    #     corner in the 2d plane.
    #     """
    #     target_point = np.sign(direction) * (FRAME_X_RADIUS, FRAME_Y_RADIUS, 0)
    #     point_to_align = self.box.get(direction)
    #     shift_val = target_point - point_to_align - buff * np.array(direction)
    #     shift_val = shift_val * abs(np.sign(direction))
    #     self.shift(shift_val)
    #     return self

    def next_to(
        self,
        target: Item | Vect,
        direction: Vect = RIGHT,
        buff: float = DEFAULT_ITEM_TO_ITEM_BUFF,
        aligned_edge: Vect = ORIGIN,
        coor_mask: Iterable = (1, 1, 1)
    ) -> Self:
        '''
        将该物件放到 ``target`` 旁边

        Position this item next to ``target``.
        '''
        if isinstance(target, Item):
            target = target.box.get(aligned_edge + direction)

        point_to_align = self.box.get(aligned_edge - direction)
        self.shift((target - point_to_align + buff * direction) * coor_mask)
        return self

    # TODO: shift_onto_screen

    def set_coord(self, value: float, dim: int, direction: Vect = ORIGIN) -> Self:
        curr = self.box.coord(dim, direction)
        shift_vect = np.zeros(3)
        shift_vect[dim] = value - curr
        self.shift(shift_vect)
        return self

    def set_x(self, x: float, direction: Vect = ORIGIN) -> Self:
        return self.set_coord(x, 0, direction)

    def set_y(self, y: float, direction: Vect = ORIGIN) -> Self:
        return self.set_coord(y, 1, direction)

    def set_z(self, z: float, direction: Vect = ORIGIN) -> Self:
        return self.set_coord(z, 2, direction)

    # endregion


class GroupClass(Item):
    def __init__(self, *items: Item, **kwargs):
        super().__init__(**kwargs)
        self.add(*items)


ItemT = TypeVar('ItemT', bound=Item)


# 该方法用于方便类型检查以及补全提示
# 在执行时和直接调用 GroupClass 没有区别
def Group(*items: ItemT) -> Item | ItemT:
    '''
    将 ``items`` 打包为一个 ``Group``，方便属性的设定

    Pack ``items`` into a ``Group`` for convenient property setting.
    '''
    return GroupClass(*items)


class BatchOp:
    '''
    批量操作，对该实例的调用都会作用到传入的物件上

    如果对每个物件的调用返回的都是 ``None`` 或者物件本身，
    那么对该实例的调用会返回 ``self``

    如果对物件的调用存在其它返回值，
    那么会将每个物件调用后的返回值放入列表中返回

    如果 ``paired`` 为 ``False``，
    那么物件有返回值时则返回 ``[val1, val2, ...]``，
    否则返回 ``[(item1, val1), (item2, val2), ...]``


    Batch operation, all calls to this instance will apply to the passed items.

    If every call to an item returns ``None`` or the item itself,
    calling this instance will return ``self``.

    If there are other return values for the item calls,
    each return value will be put into a list and returned.

    If ``paired`` is ``False``,
    and items has a return values, it will return ``[val1, val2, ...]``,
    otherwise, it will return ``[(item1, val1), (item2, val2), ...]``.
    '''

    class NFRB(enum.Enum):
        '''
        abbr of ``NotFoundReturnBehaviour``

        ``BatchOp.NFRB.Auto`` 会在 ``method_name.startswith('get')`` 为 True 时自动成为 ``EmptyList``

        ``BatchOp.NFRB.Auto`` become ``EmptyList`` if ``method_name.startswith('get')`` is ``True``
        '''
        Auto = 0
        EmptyList = 1
        Self = 2

    def __init__(
        self,
        *items: Item,
        paired: bool = False,
        warning: bool = True,
        nfrb: NFRB = NFRB.Auto
    ):
        self.items = items
        self.paired = paired
        self.warning = warning
        self.nfrb = nfrb

    def __getattr__(self, method_name: str):
        def func(*args, **kwargs):
            ret_list = []
            found = False

            # 遍历物件进行方法调用
            # Interate over items for method call
            for item in self.items:
                if not hasattr(item, method_name):
                    continue

                if isinstance(getattr(item.__class__, method_name), property):
                    # 如果是 `property`，用 lambda 封装成 `Callable`
                    # If the attribute is a property, create a lambda function to wrap it.
                    attr = lambda: getattr(item, method_name)
                else:
                    attr = getattr(item, method_name)

                if not callable(attr):
                    continue
                found = True

                ret = attr(*args, **kwargs)
                if ret is not None and ret is not item:
                    ret_list.append((item, ret) if self.paired else ret)

            # 如果没有任何物件调用了方法，那么进行警告
            # If no item called the method, issue a warning
            if not found:
                nfrb = self.nfrb
                if self.nfrb == BatchOp.NFRB.Auto and method_name.startswith('get'):
                    nfrb = BatchOp.NFRB.EmptyList

                if self.warning and nfrb != BatchOp.NFRB.EmptyList:
                    frame = inspect.currentframe().f_back
                    # TODO: i18n
                    log.warning(f'[{frame.f_code.co_filename}:{frame.f_lineno}] 没有物件拥有 `{method_name}` 方法，调用没有产生效果')

                return [] if nfrb == BatchOp.NFRB.EmptyList else self

            return ret_list or self

        return func
