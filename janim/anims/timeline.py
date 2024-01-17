from __future__ import annotations

import inspect
import math
from abc import ABCMeta, abstractmethod
from contextvars import ContextVar
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, TYPE_CHECKING

from janim.anims.animation import Animation
from janim.anims.display import Display
from janim.logger import log

if TYPE_CHECKING:   # pragma: no cover
    from janim.items.item import Item


class Timeline(metaclass=ABCMeta):
    ctx_var: ContextVar[Timeline] = ContextVar('Timeline.ctx_var', default=None)

    @dataclass
    class TimeOfCode:
        time: float
        line: int

    @dataclass
    class TimedItemData:
        time: float
        data: Item.StoredData

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_time: float = 0
        self.times_of_code: list[Timeline.TimeOfCode] = []

        self.animations: list[Animation] = []

        self.item_stored_datas: defaultdict[Item, list[Timeline.TimedItemData]] = defaultdict(list)
        self.item_display_times: dict[Item, int] = {}

    @abstractmethod
    def build(self) -> None: ...

    def _build(self) -> None:
        token = self.ctx_var.set(self)
        try:
            self._build_frame = inspect.currentframe()
            self.build()
        finally:
            self.ctx_var.reset(token)

    def register(self, item: Item) -> None:
        self.item_stored_datas[item]

    def get_build_lineno(self) -> int | None:
        frame = inspect.currentframe().f_back
        while frame is not None:
            f_back = frame.f_back

            if f_back is self._build_frame:
                return frame.f_lineno

            frame = f_back

        return None     # pragma: no cover

    def forward(self, dt: float) -> None:
        if dt <= 0:
            raise ValueError('dt 必须大于 0')

        self.detect_changes_of_all()
        self.current_time += dt

        self.times_of_code.append(
            Timeline.TimeOfCode(
                self.current_time,
                self.get_build_lineno() or -1
            )
        )

    def forward_to(self, t: float) -> None:
        self.forward(t - self.current_time)

    def detect_changes_of_all(self) -> None:
        for item, datas in self.item_stored_datas.items():
            self._detect_change(item, datas)

    def detect_changes(self, items: Iterable[Item], *, as_time: float | None = None) -> None:
        for item in items:
            self._detect_change(item, self.item_stored_datas[item], as_time=as_time)

    def _detect_change(
        self,
        item: Item,
        datas: list[Timeline.TimedItemData],
        *,
        as_time: float | None = None
    ) -> None:
        if not datas:
            datas.append(Timeline.TimedItemData(0, item.store_data()))

        elif datas[-1].data.is_changed():
            if as_time is None:
                as_time = self.current_time

            if as_time < datas[-1].time:
                # TOOD: 明确是什么物件
                raise RuntimeError('记录物件数据失败，可能是因为物件处于动画中')

            elif as_time == datas[-1].time:
                datas[-1].data = item.store_data()

            else:  # as_time > datas[-1].time
                datas.append(Timeline.TimedItemData(as_time, item.store_data()))

    def get_stored_data_at_time(self, item: Item, t: float) -> Timeline.TimedItemData:
        datas = self.item_stored_datas[item]

        if not datas:
            raise ValueError('Not stored')

        ret = None
        for data in reversed(datas):
            if data.time <= t:
                ret = data
                break

        assert ret is not None
        return ret

    def _show(self, item: Item) -> None:
        self.item_display_times.setdefault(item, self.current_time)

    def show(self, root: Item, *, self_only=False) -> None:
        self._show(root)
        if not self_only:
            for item in root.descendants():
                self._show(item)

    def _hide(self, item: Item) -> None:
        time = self.item_display_times.pop(item, None)
        if time is None:
            return

        duration = self.current_time - time
        self.animations.append(Display(item, at=time, duration=duration))

    def hide(self, root: Item, *, self_only=False) -> None:
        self._hide(root)
        if not self_only:
            for item in root.descendants():
                self._hide(item)

    # region debug

    def dbg_time(self, ext_msg: str = '') -> None:  # pragma: no cover
        if ext_msg:
            ext_msg = f'[{ext_msg}]  '

        time = round(self.current_time, 2)

        minutes = int(time // 60)
        time %= 60

        hours = minutes // 60
        minutes %= 60

        seconds = math.floor(time)
        ms = int((time - seconds) * 1e3)

        times = []
        if hours != 0:
            times.append(f'{hours}h')
        times.append(f'{minutes:>3d}m' if minutes != 0 else ' ' * 4)
        times.append(f'{seconds:>3d}s')
        times.append(f'{ms:>4d}ms' if ms != 0 else ' ' * 5)

        log.debug(f't={"".join(times)}  {ext_msg}at build.{self.get_build_lineno()}')

    # endregion
