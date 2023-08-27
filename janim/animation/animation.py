from typing import Callable
from abc import abstractmethod, ABCMeta

from enum import Enum

from janim.constants import *
from janim.items.item import Item
from janim.items.vitem import VItem
from janim.utils.rate_functions import RateFunc, smooth
from janim.utils.simple_functions import clip

class Animation:
    '''
    动画基类
    - 创建一个从 `begin_time` 持续至 `begin_time + run_time` 的动画
    - 指定 `rate_func` 可以设定插值函数，默认为 `smooth` 即平滑插值
    - 实现了对 `begin`、`interpolate` 和 `finish` 的封装，子类进行功能实现
    '''
    class _State(Enum):
        '''
        标记当前动画的执行状态
        '''
        BeforeExec = 0
        OnExec = 1
        AfterExec = 2

    def __init__(
        self,
        begin_time: float = 0.0,
        run_time: float = DEFAULT_RUN_TIME,
        rate_func: RateFunc = smooth,
    ) -> None:
        self.begin_time = begin_time
        self.run_time = run_time
        self.rate_func = rate_func

        self.state = Animation._State.BeforeExec
    
    def set_scene_instance(self, scene) -> None:
        from janim.scene.scene import Scene
        self.scene: Scene = scene

    def get_alpha(self, elapsed: float) -> float:
        '''
        根据 `elapsed` 已过时间，得到其从 `begin_time` 至 `begin_time + run_time` 的占比
        '''
        return (elapsed - self.begin_time) / self.run_time

    def update(self, elapsed, dt) -> None:
        '''
        根据 `elapsed` 已过时间，更新动画状态并进行处理

        - 当 `elapsed` 达到 `begin_time`，则会调用 `begin` 且进入 `OnExec` 状态，在该状态中会持续调用 `interpolate` 进行动画插值；
        - 当 `elapsed` 继续前进，达到 `begin_time + run_time`，则会调用 `finish` 且进入 `AfterExec` 状态，结束当前动画的处理。
        '''
        # 使用 < 判断处于前一状态，使用 >= 判断进入后一状态

        # 检查并切换状态
        if self.state == self._State.BeforeExec and elapsed >= self.begin_time:
            self.begin()
            self.state = self._State.OnExec
        
        if self.state == self._State.OnExec and elapsed >= self.begin_time + self.run_time:
            self.finish()
            self.state = self._State.AfterExec

        # 常规处理
        if self.state == self._State.OnExec:
            self.interpolate(self.rate_func(self.get_alpha(elapsed)))
        
    def begin(self) -> None:
        '''
        在该方法中编写用于初始化动画执行的代码，
        由子类实现具体功能
        '''
        pass

    def interpolate(self, alpha) -> None:
        '''
        在该方法中编写用于插值动画的代码，
        由子类实现具体功能
        '''
        pass

    def finish(self) -> None:
        '''
        在该方法中编写用于结束动画执行的代码，
        由子类实现具体功能
        '''
        pass

    def finish_all(self) -> None:
        '''
        用于整个动画执行的扫尾，以保证达到 `AfterExec` 状态
        '''
        if self.state == self._State.BeforeExec:
            self.begin()
            self.state = self._State.OnExec

        if self.state == self._State.OnExec:
            self.finish()
            self.state = self._State.AfterExec

    def make_visible(self, item: Item) -> None:
        '''使物体、其子物件及其父物件可见'''
        toplevel_item = item.get_toplevel_item()
        if toplevel_item is not self.scene:
            self.scene.add(toplevel_item, make_visible=False)
        item.set_visible(True, True, True)


class ItemAnimation(Animation, metaclass=ABCMeta):
    '''
    物件动画的基类

    - 会对物件的 family 逐一应用插值
    - 指定 `lag_ratio` 即可起到依次执行的效果
    '''
    def __init__(
        self,
        item_for_anim: Item,
        lag_ratio: float = 0,
        skip_null_items: bool = False,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.item_for_anim = item_for_anim
        self.lag_ratio = lag_ratio
        self.skip_null_items = skip_null_items
    
    def get_sub_alpha(
        self,
        alpha: float,
        index: int,
        num_subitems: int
    ) -> float:
        '''依据 `lag_ratio` 得到特定子物件的 sub_alpha'''
        # TODO: [L] make this more understanable
        lag_ratio = self.lag_ratio
        full_length = (num_subitems - 1) * lag_ratio + 1
        value = alpha * full_length
        lower = index * lag_ratio
        return clip((value - lower), 0, 1)

    @abstractmethod
    def create_interpolate_datas(self) -> tuple:
        '''
        创建用于插值的数据，由子类实现

        例如下面这个返回值，将会使 `interpolate_subitem` 的 
        `interpolate_data` 参数分别得到 (a, d), (b, e), (c, f)
        ```python
        return (
            (a, b, c),
            (d, e, f)
        )
        ```
        '''
        pass
    
    @abstractmethod
    def is_null_item(self, item: Item, interpolate_data: tuple) -> bool:
        '''
        判断是否为空物件，由子类实现

        如果指定了 `skip_null_items` 且返回值为 `True`，那么这一个子物件会被忽略
        '''
        pass
    
    def begin(self) -> None:
        # 如果物件不在场景中，那么添加到场景
        self.make_visible(self.item_for_anim)

        # 为 `interpolate_subitem`` 准备数据
        self.families = list(zip(
            self.item_for_anim.get_family(),
            zip(*self.create_interpolate_datas())
        ))
        if self.skip_null_items:
            self.families = [
                data
                for data in self.families
                if not self.is_null_item(*data)
            ]
    
    def interpolate(self, alpha) -> None:
        # 遍历所有子物件的数据，调用 `interpolate_subitem`
        for i, families in enumerate(self.families):
            sub_alpha = self.get_sub_alpha(alpha, i, len(self.families))
            self.interpolate_subitem(*families, sub_alpha)

    def finish(self) -> None:
        self.interpolate(1)
    
    def interpolate_subitem(
        self,
        item: Item,
        interpolate_data: tuple,
        alpha: float
    ) -> None:
        '''由子类实现'''
        pass

    @staticmethod
    def compute_npdata_to_copy_and_interpolate(item1: Item, item2: Item) -> list[tuple[str, str, str]]:
        '''
        依据前后数据时候有变动，
        判断哪些需要进行插值
        '''
        return [
            [
                (key, getter, setter)
                for key, getter, setter in subitem1.npdata_to_copy_and_interpolate & subitem2.npdata_to_copy_and_interpolate
                if not np.all(getattr(subitem1, key) == getattr(subitem2, key))
            ]
            for subitem1, subitem2 in zip(item1.get_family(), item2.get_family())
        ]

    @staticmethod
    def compute_triangulation_equals(item1: Item, item2: Item) -> list[bool]:
        '''
        判断两个 `Item` 的子物件的三角剖分是否相同，
        如果子物件不是 `VItem`，那么该子物件的结果为 `False`
        '''
        return [
                isinstance(subitem1, VItem) 
            and isinstance(subitem2, VItem) 
            and len(subitem1.get_triangulation()) == len(subitem2.get_triangulation())
            and np.all(subitem1.get_triangulation() == subitem2.get_triangulation())
            for subitem1, subitem2 in zip(item1.get_family(), item2.get_family())
        ]
    
    
