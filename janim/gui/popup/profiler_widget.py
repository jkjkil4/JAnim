from __future__ import annotations

import itertools as it
from collections import deque
from typing import TYPE_CHECKING

from PySide6.QtCore import QMargins, QPointF, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QVBoxLayout, QWidget

from janim.locale import get_translator
from janim.render.profiler import FrameRecord

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.popup.profiler_widget')


class ProfilerWidget(QWidget):
    def __init__(self, viewer: AnimViewer):
        super().__init__(viewer)
        self.viewer = viewer

        self.setup_ui()
        self.setup_slots()

        self.option_normalize.setChecked(True)
        self.option_normalize.setEnabled(False)  # 由于另一个功能暂未实现，先禁用

        self.setWindowTitle(_('Render Profiler'))
        self.resize(800, 600)

    def setup_ui(self) -> None:
        self.graph = ProfilerGraph(self.viewer)

        layout = QVBoxLayout()
        layout.setContentsMargins(QMargins())
        layout.setSpacing(0)
        layout.addWidget(self.setup_options())
        layout.addWidget(self.graph, 1)

        self.setLayout(layout)

    def setup_options(self) -> QWidget:
        self.option_normalize = QCheckBox(_('Normalize'))
        layout = QHBoxLayout()
        layout.addWidget(self.option_normalize)
        layout.addStretch()

        self.options = QWidget()
        self.options.setLayout(layout)

        return self.options

    def setup_slots(self) -> None:
        self.option_normalize.stateChanged.connect(lambda flag: self.graph.set_normalize(flag))


class ProfilerGraph(QWidget):
    RECORDS_MAXLEN = 200
    FILL_COLOR = QColor('#1e1e1e')

    def __init__(self, viewer: AnimViewer):
        super().__init__()
        self.viewer = viewer
        self.viewer.glw.setup_profiler(self._on_frame_recorded)
        self.destroyed.connect(self.viewer.glw.teardown_profiler)

        self._normalize: bool = False

        self._rendered_records: deque[FrameRecord] = deque(maxlen=self.RECORDS_MAXLEN)
        self._pending_records: list[FrameRecord] = []

        self._resize_timer = QTimer(interval=50, singleShot=True)
        self._resize_timer.timeout.connect(self._on_resize_timeout)

        self._buffer_pixmap = self._new_buffer_pixmap(self.size())
        self._buffered: bool = False

        colors_hex = [
            '#88C0D0',
            '#A3BE8C',
            '#EBCB8B',
            '#BF616A',
            '#B48EAD',
            '#5E81AC',
            '#D08770',
            '#81A1C1',
            '#FF79C6',
            '#BD93F9',
            '#50FA7B',
            '#F1FA8C',
            '#46D9FF',
            '#FFB86C',
            '#ff757f',
            '#82aaff',
        ]
        self._colors = it.cycle([QColor(hex) for hex in colors_hex])
        self._color_cache: dict[str, QColor] = {}

    def set_normalize(self, flag: bool) -> None:
        self._normalize = flag
        self.update()

    def _on_frame_recorded(self, frame: FrameRecord) -> None:
        self._pending_records.append(frame)
        self.update()

    # region buffer pixmap

    def resizeEvent(self, event, /) -> None:
        if not self._resize_timer.isActive():
            self._resize_timer.start()
        super().resizeEvent(event)

    def _on_resize_timeout(self) -> None:
        size = self.size()
        if size != self._buffer_pixmap.size():
            self._buffer_pixmap = self._new_buffer_pixmap(self.size())
            self._buffered = False
            self.update()

    def _new_buffer_pixmap(self, size: QSize) -> QPixmap:
        pixmap = QPixmap(size)
        pixmap.fill(self.FILL_COLOR)
        return pixmap

    def _update_buffer_pixmap(self) -> None:
        # 如果没有新的记录，并且缓冲区没有重置过，那么直接复用
        if not self._pending_records and self._buffered:
            return

        pending_count = len(self._pending_records)
        self._rendered_records.extend(self._pending_records)
        self._pending_records.clear()

        # 如果缓冲区重置过，则全量绘制，否则增量绘制
        if not self._buffered:
            self._buffered = True

            records_len = len(self._rendered_records)

            painter = QPainter(self._buffer_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._render_records(painter, 0, records_len - 1, None)

        else:
            left_idx = len(self._rendered_records) - pending_count
            left_idx = max(0, left_idx - 1)  # 因为需要 pairwise 基于前一个延伸绘制，所以 -1
            right_idx = len(self._rendered_records) - 1

            left = self._record_idx_to_pixel_x(left_idx)
            right = self._record_idx_to_pixel_x(right_idx)
            delta_x = right - left

            # 先将前一次 buffer 偏移 -delta_x
            # self._buffer_pixmap.fill(self.FILL_COLOR)
            self._buffer_pixmap.scroll(-delta_x, 0, self._buffer_pixmap.rect())

            # 然后再绘制新的部分
            painter = QPainter(self._buffer_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(
                QRect(self.width() - delta_x, 0, delta_x, self.height()), self.FILL_COLOR
            )
            self._render_records(painter, left_idx, right_idx, None)

    def _render_records(
        self,
        painter: QPainter,
        left_idx: int,
        right_idx: int,
        max_height: bool | None,  # TODO
    ) -> None:
        """
        指定 ``_rendered_records`` 中的一个区段渲染到 ``pixmap`` 中
        """
        to_pixel_y = self._y_ratio_to_pixel_y

        for i1, i2 in it.pairwise(range(left_idx, right_idx + 1)):
            x1 = self._record_idx_to_pixel_x(i1)
            x2 = self._record_idx_to_pixel_x(i2)

            record1 = self._rendered_records[i1]
            record2 = self._rendered_records[i2]

            time_pairs: list[tuple[str, float, float]] = list(self._iter_times(record1, record2))
            total_time1 = sum(x[1] for x in record1.times)
            total_time2 = sum(x[1] for x in record2.times)

            time1, time2 = 0, 0
            for name, t1, t2 in time_pairs:
                time1p = time1 + t1
                time2p = time2 + t2
                points = [
                    QPointF(x1, to_pixel_y(time1 / total_time1)),
                    QPointF(x2, to_pixel_y(time2 / total_time2)),
                    QPointF(x2, to_pixel_y(time2p / total_time2)),
                    QPointF(x1, to_pixel_y(time1p / total_time1)),
                ]

                polygon = QPolygonF(points)

                base_color = self._get_color_for_name(name)

                fill_color = QColor(base_color)
                fill_color.setAlpha(190)
                painter.setBrush(fill_color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPolygon(polygon)

                stroke_color = QColor(base_color)
                stroke_color.setAlpha(255)
                painter.setPen(stroke_color)
                painter.drawLine(points[-1], points[-2])

                time1, time2 = time1p, time2p

    def _record_idx_to_pixel_x(self, idx: int) -> int:
        """
        将 ``_rendered_records`` 中的下标转换为对应的像素 ``x`` 坐标（有取整）
        """
        # 相当于完整 RECORDS_MAXLEN 长度列表中的哪个下标
        full_idx = self.RECORDS_MAXLEN - (len(self._rendered_records) - idx)
        # 在画面中的横向比例
        ratio = full_idx / (self.RECORDS_MAXLEN - 1)  # 因为最后一个点要贴到最右侧，所以需要 -1

        return round(ratio * self.width())

    def _y_ratio_to_pixel_y(self, ratio: float) -> float:
        """
        将从底部到顶部的比率转为对应的像素 ``y`` 坐标
        """
        return self.height() * (1 - ratio)

    @staticmethod
    def _iter_times(record1: FrameRecord, record2: FrameRecord):
        """
        同时遍历 ``record1`` 和 ``record2`` 的 ``times``

        对于双方记录的类型，有如下的三种情况：

        - 若某种类型双方都有，则 ``yield (name, t1, t2)`` 表示分别的时间
        - 若某种类型只有 ``record1`` 有，则 ``yield (name, t1, 0)`` 即后者置为 0
        - 若某种类型只有 ``record2`` 有，则 ``yield (name, 0, t2)`` 即前者置为 0
        """
        idx1 = 0
        idx2 = 0
        times1 = record1.times
        times2 = record2.times

        while idx1 != len(times1) or idx2 != len(times2):
            if idx1 == len(times1):
                str2, t2 = times2[idx2]
                yield (str2, 0, t2)
                idx2 += 1
                continue
            if idx2 == len(times2):
                str1, t1 = times1[idx1]
                yield (str1, t1, 0)
                idx1 += 1
                continue

            str1, t1 = times1[idx1]
            str2, t2 = times2[idx2]
            if str1 < str2:
                yield (str1, t1, 0)
                idx1 += 1
            elif str1 > str2:
                yield (str2, 0, t2)
                idx2 += 1
            else:
                yield (str1, t1, t2)
                idx1 += 1
                idx2 += 1

    def _get_color_for_name(self, name: str) -> QColor:
        """
        得到某种类型所对应的绘制颜色

        在单次程序中保证多次查询同一个类型的结果相同，但不保证每次程序结果相同
        """
        if name in self._color_cache:
            return self._color_cache[name]
        color = self._color_cache[name] = next(self._colors)
        return color

    # endregion

    # region paint

    def paintEvent(self, event, /) -> None:
        self._update_buffer_pixmap()

        painter = QPainter(self)

        if not self._rendered_records:
            self._draw_centered_text(painter, _('No Data'))
            return

        painter.drawPixmap(QPointF(), self._buffer_pixmap)
        if self._normalize:
            self._draw_percentage_hlines(painter)
        self._draw_legend(painter)

    def _draw_centered_text(self, painter, text):
        painter.setPen(Qt.GlobalColor.gray)
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

    def _draw_percentage_hlines(self, painter: QPainter) -> None:
        pen = QPen(QColor(255, 255, 255, 180))
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)

        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        w, h = self.size().toTuple()
        for i in range(1, 4):
            percent = i * 25
            y = h - (h * (percent / 100.0))
            painter.drawLine(0, int(y), w, int(y))
            painter.drawText(5, int(y) - 2, f'{percent}%')

    def _draw_legend(self, painter) -> None:
        painter.setPen(Qt.GlobalColor.white)
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        metrics = QFontMetrics(font)

        margin = 10
        x = margin
        y = margin
        row_height = metrics.height() + 4
        max_legend_width = 250

        for name, color in self._color_cache.items():
            painter.fillRect(x, y, 12, 12, color)  # 直接用 fillRect 比 drawRect 快

            text_y = y + metrics.ascent() - 1
            painter.drawText(x + 16, text_y, name)

            text_width = metrics.horizontalAdvance(name)
            item_width = 16 + text_width + 15

            x += item_width
            if x > max_legend_width:
                x = margin
                y += row_height

    # endregion
