from typing import TYPE_CHECKING, List, Dict

import itertools  # 【新增】用于高效切片

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QTimer, Qt, QPointF, QRectF
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QFontMetrics,
    QPolygonF,
    QPixmap,
)

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer


class ProfilerWidget(QWidget):
    def __init__(self, parent: "AnimViewer"):
        super().__init__()
        self.viewer = parent
        self.setWindowTitle("Render Profiler (High Performance)")
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.graph_view = ProfilerGraph(self.viewer)
        layout.addWidget(self.graph_view)


class ProfilerGraph(QWidget):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer

        # --- 配置项 ---
        self.view_range_frames = 120
        self.refresh_rate_ms = 60

        # --- 内部状态 ---
        self.color_cache: Dict[str, QColor] = {}
        self.sorted_keys_cache: List[str] = []

        # 【优化A】双重缓冲：用于存储绘制好的图像
        self._buffer_pixmap = QPixmap()
        self._dirty = False  # 标记是否需要重绘
        self._last_recorded_item = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timeout)
        self.timer.start(self.refresh_rate_ms)
        self.timer = QTimer(self)
        # 定时器只负责标记数据“脏了”并请求更新，不直接绘图
        self.timer.timeout.connect(self._on_timeout)
        self.timer.start(self.refresh_rate_ms)

        self.palette = [
            "#88C0D0",
            "#A3BE8C",
            "#EBCB8B",
            "#BF616A",
            "#B48EAD",
            "#5E81AC",
            "#D08770",
            "#81A1C1",
            "#FF79C6",
            "#BD93F9",
            "#50FA7B",
            "#F1FA8C",
            "#46D9FF",
            "#FFB86C",
            "#ff757f",
            "#82aaff",
        ]

    def _on_timeout(self):
        """定时器回调：只处理数据准备，不直接操作 UI"""
        if not hasattr(self.viewer, "built") or not self.viewer.built:
            return
        # 触发重绘请求，系统会在合适的时候调用 paintEvent
        self._dirty = True
        self.update()

    def _get_color_for_key(self, key: str, index: int) -> QColor:
        if key in self.color_cache:
            return self.color_cache[key]
        hash_idx = abs(hash(key))
        hex_color = self.palette[hash_idx % len(self.palette)]
        color = QColor(hex_color)
        self.color_cache[key] = color
        return color

    def paintEvent(self, event):
        """
        【优化B】绘制事件：
        现在这里只负责两件事：
        1. 如果缓冲区是脏的(有新数据)或者尺寸变了，重新生成缓冲区图片。
        2. 将缓冲区图片画到屏幕上。
        """
        current_size = self.size()

        # 如果 pixmap 大小不对，或者数据更新了，才进行昂贵的重绘逻辑
        if (self._buffer_pixmap.size() != current_size) or self._dirty:
            self._update_buffer_pixmap(current_size)
            self._dirty = False  # 重置脏标记

        # 极速绘制：只是把图片贴上去
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._buffer_pixmap)

    def _update_buffer_pixmap(self, size):
        """核心绘图逻辑：绘制到内存图片中"""
        w, h = size.width(), size.height()

        # 初始化 Pixmap（如果尺寸变了才重建，否则复用）
        if self._buffer_pixmap.size() != size:
            self._buffer_pixmap = QPixmap(size)

        # 针对 Pixmap 的 Painter
        self._buffer_pixmap.fill(QColor("#1e1e1e"))  # 清除背景
        painter = QPainter(self._buffer_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 获取数据
        if not hasattr(self.viewer, "built") or not self.viewer.built:
            self._draw_centered_text(painter, "Waiting for renderer...", w, h)
            painter.end()
            return

        profiler = self.viewer.built.profiler
        total_frames_history = len(profiler.history)

        if total_frames_history == 0:
            self._draw_centered_text(painter, "No Data", w, h)
            painter.end()
            return

        # 【优化C】高效数据切片：不复制整个列表，只取最后 N 个
        # itertools.islice 对 deque 非常友好，不会遍历整个历史
        start_index = max(0, total_frames_history - self.view_range_frames)
        # 注意：这里转换成 list 依然只包含最多 120 个元素，极快
        render_data = list(
            itertools.islice(profiler.history, start_index, total_frames_history)
        )
        data_count = len(render_data)

        if data_count == 0:
            painter.end()
            return

        # 更新 Keys (为了性能，每 10 次刷新或者 Key 数量不对时才重新全量扫描 Key 也可以，这里暂且保留)
        current_frame_keys = set()
        for record in render_data:
            current_frame_keys.update(record.item_times.keys())
        for key in current_frame_keys:
            if key not in self.sorted_keys_cache:
                self.sorted_keys_cache.append(key)

        # --- 预计算坐标 ---
        pixels_per_frame = w / max(1, (self.view_range_frames - 1))
        num_keys = len(self.sorted_keys_cache)

        # 预分配数组，避免 append
        # stack_tops[key_idx][frame_idx]
        stack_tops = [[0.0] * data_count for _ in range(num_keys)]

        # 一次循环计算所有堆叠高度
        for i, record in enumerate(render_data):
            total_time = sum(record.item_times.values())
            accumulated_percent = 0.0
            inv_total = 1.0 / total_time if total_time > 0 else 0.0

            for k_idx, key in enumerate(self.sorted_keys_cache):
                val = record.item_times.get(key, 0)
                if total_time > 0:
                    accumulated_percent += val * inv_total

                # 修正浮点
                if k_idx == num_keys - 1 and total_time > 0:
                    accumulated_percent = 1.0

                stack_tops[k_idx][i] = min(1.0, accumulated_percent)

        # --- 绘制图层 (使用 PolygonF) ---
        # 记录上一层的下边界 Y 值
        prev_layer_bottom_y = [float(h)] * data_count

        # 预先计算 X 坐标数组（所有层共用）
        # x_coords[i] 对应 render_data[i] 的屏幕 x 坐标
        # render_data[0] 是最旧的 (左边)，render_data[-1] 是最新的 (右边)
        # 原逻辑：frame_offset = (data_count - 1) - i
        # x = w - (frame_offset * pixels_per_frame)
        x_coords = [
            w - ((data_count - 1 - i) * pixels_per_frame) for i in range(data_count)
        ]

        for k_idx, key in enumerate(self.sorted_keys_cache):
            current_tops = stack_tops[k_idx]

            # 【优化D】构建多边形点集
            # 一个多边形由两部分组成：
            # 1. 上边界（从左到右）
            # 2. 下边界（从右到左，闭合回去）

            points = []
            current_layer_y = []  # 暂存这一层的Y，供下一层做 Bottom

            # 1. 构建上边界 (Left -> Right)
            for i in range(data_count):
                y = h - (current_tops[i] * h)
                points.append(QPointF(x_coords[i], y))
                current_layer_y.append(y)

            # 2. 构建下边界 (Right -> Left)
            # 逆序遍历 prev_layer_bottom_y
            for i in range(data_count - 1, -1, -1):
                points.append(QPointF(x_coords[i], prev_layer_bottom_y[i]))

            # 创建多边形
            polygon = QPolygonF(points)

            # 绘制
            base_color = self._get_color_for_key(key, k_idx)
            fill_color = QColor(base_color)
            fill_color.setAlpha(190)

            stroke_color = QColor(base_color)
            stroke_color.setAlpha(255)

            painter.setBrush(QBrush(fill_color))
            pen = QPen(stroke_color)
            pen.setWidthF(0.5)
            painter.setPen(pen)

            painter.drawPolygon(polygon)

            # 更新下边界记录
            prev_layer_bottom_y = current_layer_y

        # 绘制辅助元素
        self._draw_grid(painter, w, h)
        self._draw_legend(painter, w, h)

        painter.end()  # 结束绘制，保存到 Pixmap

    def _draw_grid(self, painter, w, h):
        pen = QPen(QColor(255, 255, 255, 50))
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        for i in range(1, 4):
            percent = i * 25
            y = h - (h * (percent / 100.0))
            painter.drawLine(0, int(y), w, int(y))
            painter.drawText(5, int(y) - 2, f"{percent}%")

    def _draw_legend(self, painter, w, h):
        keys = self.sorted_keys_cache
        if not keys:
            return

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

        for i, key in enumerate(keys):
            color = self._get_color_for_key(key, i)
            painter.fillRect(x, y, 12, 12, color)  # 直接用 fillRect 比 drawRect 快

            text_y = y + metrics.ascent() - 1
            painter.drawText(x + 16, text_y, key)

            text_width = metrics.horizontalAdvance(key)
            item_width = 16 + text_width + 15

            x += item_width
            if x > max_legend_width and i < len(keys) - 1:
                x = margin
                y += row_height

    def _draw_centered_text(self, painter, text, w, h):
        painter.setPen(Qt.GlobalColor.gray)
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, text)
