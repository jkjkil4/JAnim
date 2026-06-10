from dataclasses import dataclass
from janim.timeline.core import TimelineCore


@dataclass
class PausePoint:
    at: float
    at_previous_frame: bool


class PausePointsMixin(TimelineCore):
    """
    向 :class:`~.Timeline` 提供标记暂停点的功能
    """

    PausePoint = PausePoint  # 只是为了让 PausePoint 也出现在 Timeline 的类成员中

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pause_points: list[PausePoint] = []

    def pause_point(
        self,
        *,
        offset: float = 0,
        at_previous_frame: bool = True,
    ) -> None:
        """
        标记在预览界面中，执行到当前时间点时会暂停

        .. tip::

            在 GUI 界面中，可以使用 ``Ctrl+左方向键`` 快速移动到前一个暂停点，``Ctrl+右方向键`` 快速移动到后一个

            如果没按着 ``Ctrl`` 键，则会变为在前后的动画区间之间移动

        :param offset: 表示偏移多少秒，例如 ``offset=2`` 则是当前时刻的 2s 后

        :param at_previous_frame: 控制是在前一帧暂停还是在当前帧暂停

            默认为 ``True``，因为一般情况下我们暂停时想要显示先前画面中的最后一帧，而非随后画面
            （帧的显示规则是由 JAnim 动画区间左闭右开导致的）
        """
        self.pause_points.append(PausePoint(self.current_time + offset, at_previous_frame))

    def _pause_points_to_progresses(self, preview_fps: int) -> list[int]:
        """
        将记录的暂停点转换为以 ``preview_fps`` 为基准的“帧进度”
        """
        progresses: list[int] = []

        for p in self.pause_points:
            rough_progress = p.at * preview_fps

            if rough_progress % 1 < 1e-3:  # 避免一下浮点误差
                result = int(rough_progress)
            else:
                result = int(rough_progress) + 1

            if p.at_previous_frame:
                result -= 1

            progresses.append(result)

        return progresses
