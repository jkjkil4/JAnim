try:
    import PySide6  # noqa: F401
except ImportError:
    print('使用 GUI 界面时需要安装额外模块，但是未安装')
    print('你可以使用 pip install janim[gui] 进行安装，并确保你安装在了正确的 Python 版本中')

    from janim.exception import EXITCODE_PYSIDE6_NOT_FOUND, ExitException
    raise ExitException(EXITCODE_PYSIDE6_NOT_FOUND)

import importlib.machinery
import inspect
import json
import math
import os
import sys
import time
import traceback
from bisect import bisect
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import (QByteArray, QPoint, QRect, QRectF, Qt, QTimer,
                            Signal)
from PySide6.QtGui import (QBrush, QCloseEvent, QColor, QHideEvent, QIcon,
                           QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen,
                           QWheelEvent)
from PySide6.QtWidgets import (QApplication, QFileDialog, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QSizePolicy,
                               QSplitter, QStackedLayout, QVBoxLayout, QWidget)

from janim.anims.animation import Animation, TimeRange
from janim.anims.timeline import Timeline, TimelineAnim
from janim.exception import ExitException
from janim.gui.application import Application
from janim.gui.audio_player import AudioPlayer
from janim.gui.fixed_ratio_widget import FixedRatioWidget
from janim.gui.glwidget import GLWidget
from janim.gui.precise_timer import PreciseTimer
from janim.gui.richtext_editor import RichTextEditor
from janim.gui.selector import Selector
from janim.logger import log
from janim.render.writer import VideoWriter
from janim.utils.bezier import interpolate
from janim.utils.file_ops import get_janim_dir
from janim.utils.simple_functions import clip

if TYPE_CHECKING:
    from PySide6.QtCharts import QAreaSeries, QChartView

TIMELINE_VIEW_MIN_DURATION = 0.5


class AnimViewer(QMainWindow):
    '''
    用于显示构建完成的时间轴动画

    可以使用 ``AnimViewer.views(MyTimeline().build())`` 进行直接显示
    '''
    play_finished = Signal()

    def __init__(
        self,
        anim: TimelineAnim,
        auto_play: bool = True,
        interact: bool = False,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.anim = anim
        self.interact = interact

        self.setWindowIcon(QIcon(os.path.join(get_janim_dir(), 'gui', 'favicon.ico')))

        self.setup_ui()
        self.move_to_position()
        self.socket = None
        if interact:
            self.setup_socket()

        self.timeline_view.value_changed.connect(self.on_value_changed)
        self.timeline_view.dragged.connect(lambda: self.set_play_state(False))
        self.timeline_view.space_pressed.connect(lambda: self.switch_play_state())
        self.timeline_view.value_changed.emit(0)

        self.btn_export.clicked.connect(self.on_export_clicked)

        self.play_timer = PreciseTimer(1 / self.anim.cfg.preview_fps, self)
        self.play_timer.timeout.connect(self.on_play_timer_timeout)
        if auto_play:
            self.switch_play_state()

        self.audio_player: AudioPlayer | None = None
        self.setup_audio_player()

        self.fps_counter = 0
        self.fps_record_start = time.time()

        self.glw.rendered.connect(self.on_glw_rendered)

    # region setup_ui

    def setup_ui(self) -> None:
        self.setup_menu_bar()
        self.setup_status_bar()
        self.setup_central_widget()

    def setup_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        menu_functions = menu_bar.addMenu('功能')

        self.action_stay_on_top = menu_functions.addAction('窗口置前')
        self.action_stay_on_top.setCheckable(True)
        self.action_stay_on_top.setShortcut('Ctrl+T')
        self.action_stay_on_top.toggled.connect(self.on_stay_on_top_toggled)
        self.action_stay_on_top.setChecked(True)

        menu_functions.addSeparator()

        self.action_reload = menu_functions.addAction('重新构建')
        self.action_reload.setShortcut('Ctrl+L')
        self.action_reload.triggered.connect(self.on_rebuild_triggered)

        menu_functions.addSeparator()

        self.action_select = menu_functions.addAction('子物件选择')
        self.action_select.setShortcut('Ctrl+S')
        self.action_select.triggered.connect(self.on_select_triggered)
        self.selector: Selector | None = None

        self.action_richtext_edit = menu_functions.addAction('富文本编辑')
        self.action_richtext_edit.setShortcut('Ctrl+R')
        self.action_richtext_edit.triggered.connect(self.on_richtext_edit_triggered)
        self.richtext_editor: RichTextEditor | None = None

    def setup_status_bar(self) -> None:
        self.fps_label = QLabel()
        self.time_label = QLabel()
        self.btn_export = QPushButton()
        self.btn_export.setIcon(QIcon(os.path.join(get_janim_dir(), 'gui', 'export.png')))
        self.btn_export.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        stb = self.statusBar()
        stb.setContentsMargins(0, 0, 0, 0)
        stb.addWidget(self.fps_label)
        stb.addPermanentWidget(self.time_label)
        stb.addPermanentWidget(self.btn_export)

    def setup_central_widget(self) -> None:
        self.glw = GLWidget(self.anim, self)
        self.overlay = QWidget(self)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.stkLayout = QStackedLayout()
        self.stkLayout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.stkLayout.addWidget(self.glw)
        self.stkLayout.addWidget(self.overlay)

        self.stkWidget = QWidget(self)
        self.stkWidget.setLayout(self.stkLayout)

        self.fixed_ratio_widget = FixedRatioWidget(
            self.stkWidget,
            (self.anim.cfg.pixel_width, self.anim.cfg.pixel_height)
        )

        self.timeline_view = TimelineView(self.anim)
        self.timeline_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.vsplitter = QSplitter()
        self.vsplitter.setOrientation(Qt.Orientation.Vertical)
        self.vsplitter.addWidget(self.fixed_ratio_widget)
        self.vsplitter.addWidget(self.timeline_view)
        self.vsplitter.setSizes([400, 100])
        self.vsplitter.setStyleSheet('''QSplitter { background: rgb(25, 35, 45); }''')

        self.setCentralWidget(self.vsplitter)
        self.setMinimumSize(200, 160)
        self.resize(800, 608)
        self.setWindowTitle('JAnim Graphics')

    def move_to_position(self) -> None:
        window_position = self.anim.cfg.wnd_pos
        window_monitor = self.anim.cfg.wnd_monitor

        if len(window_position) != 2 or window_position[0] not in 'UOD' or window_position[1] not in 'LOR':
            log.warning(f'wnd_pos has wrong argument "{window_position}".')
            window_position = 'UR'

        screens = QApplication.screens()
        if window_monitor < len(screens):
            screen = screens[window_monitor]
        else:
            screen = screens[0]
            log.warning(f'wnd_monitor has invaild value {window_monitor}, please use 0~{len(screens) - 1} instead.')
        screen_size = screen.availableSize()

        if window_position[1] == 'O':
            width = screen_size.width()
            x = 0
        else:
            width = screen_size.width() / 2
            x = 0 if window_position[1] == 'L' else width

        if window_position[0] == 'O':
            height = screen_size.height()
            y = 0
        else:
            height = screen_size.height() / 2
            y = 0 if window_position[0] == 'U' else height

        self.move(x, y)
        self.resize(width, height)

    # endregion

    def setup_audio_player(self) -> None:
        if self.anim.timeline.has_audio() and self.audio_player is None:
            self.audio_player = AudioPlayer(self.anim.cfg.audio_framerate)

    # region socket

    def setup_socket(self) -> None:
        from PySide6.QtNetwork import QHostAddress, QUdpSocket

        self.shared_socket = QUdpSocket()
        ret = self.shared_socket.bind(40565, QUdpSocket.BindFlag.ShareAddress | QUdpSocket.BindFlag.ReuseAddressHint)
        log.debug(f'shared_socket.bind(40565, ShareAddress | ReuseAddressHint) = {ret}')
        self.shared_socket.readyRead.connect(self.on_shared_ready_read)

        self.socket = QUdpSocket()
        self.socket.bind()

        self.socket.readyRead.connect(self.on_ready_read)

        self.clients: list[tuple[QHostAddress, int]] = []
        self.lineno = -1

        log.info(f'交互端口已在 {self.socket.localPort()} 开启')
        self.setWindowTitle(f'{self.windowTitle()} [{self.socket.localPort()}]')

    def on_shared_ready_read(self) -> None:
        while self.shared_socket.hasPendingDatagrams():
            datagram = self.shared_socket.receiveDatagram()
            try:
                tree = json.loads(datagram.data().toStdString())
                assert 'janim' in tree

                janim = tree['janim']
                cmdtype = janim['type']

                if cmdtype == 'find':
                    msg = json.dumps(dict(
                        janim=dict(
                            type='find_re',
                            data=dict(
                                port=self.socket.localPort(),
                                file_path=os.path.abspath(inspect.getfile(self.anim.timeline.__class__))
                            )
                        )
                    ))
                    self.socket.writeDatagram(
                        QByteArray.fromStdString(msg),
                        datagram.senderAddress(),
                        datagram.senderPort()
                    )

            except Exception:
                traceback.print_exc()

    def on_ready_read(self) -> None:
        while self.socket.hasPendingDatagrams():
            datagram = self.socket.receiveDatagram()
            try:
                tree = json.loads(datagram.data().toStdString())
                assert 'janim' in tree

                janim = tree['janim']

                match janim['type']:
                    case 'register_client':
                        self.clients.append((datagram.senderAddress(), datagram.senderPort()))
                        self.send_lineno(self.lineno)

                    # 重新构建
                    case 'file_saved':
                        if os.path.samefile(janim['file_path'], inspect.getmodule(self.anim.timeline).__file__):
                            self.on_rebuild_triggered()

                    # 重新加载
                    case 'reload':
                        file_path = janim['file_path']
                        for module in sys.modules.values():
                            module_file_path = getattr(module, '__file__', None)
                            if module_file_path is not None and os.path.samefile(module_file_path, file_path):
                                importlib.reload(module)
                                log.info(f'已重新加载 {file_path}')
                                break
                        else:
                            log.error(f'{file_path} 之前没被导入过')

            except Exception:
                traceback.print_exc()

    def send_lineno(self, line: int) -> None:
        msg = json.dumps(dict(
            janim=dict(
                type='lineno',
                data=line
            )
        ))
        for client in self.clients:
            self.socket.writeDatagram(
                QByteArray.fromStdString(msg),
                *client
            )

    # endregion

    # region events

    def hideEvent(self, event: QHideEvent) -> None:
        super().hideEvent(event)
        self.play_timer.stop()

    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)
        if self.interact:
            msg = json.dumps(dict(
                janim=dict(
                    type='close_event'
                )
            ))
            for client in self.clients:
                self.socket.writeDatagram(
                    QByteArray.fromStdString(msg),
                    *client
                )

    # endregion

    # region slots

    def on_value_changed(self, value: int) -> None:
        time = self.timeline_view.progress_to_time(value)

        if self.socket is not None:
            line = self.anim.timeline.get_lineno_at_time(time)

            if line != self.lineno:
                self.lineno = line

                self.send_lineno(line)

        self.glw.set_time(time)
        self.time_label.setText(f'{time:.1f}/{self.anim.global_range.duration:.1f} s')

    def on_play_timer_timeout(self) -> None:
        if self.anim.timeline.has_audio():
            samples = self.anim.timeline.get_audio_samples_of_frame(self.anim.cfg.preview_fps,
                                                                    self.anim.cfg.audio_framerate,
                                                                    self.timeline_view.progress())
            self.audio_player.write(samples.tobytes())

        self.timeline_view.set_progress(self.timeline_view.progress() + 1)
        if self.timeline_view.at_end():
            self.play_finished.emit()
            self.play_timer.stop()

    def on_stay_on_top_toggled(self, flag: bool) -> None:
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, flag)
        if visible:
            self.setVisible(True)

    def on_rebuild_triggered(self) -> None:
        module = inspect.getmodule(self.anim.timeline)
        progress = self.timeline_view.progress()
        preview_fps = self.anim.cfg.preview_fps

        loader = importlib.machinery.SourceFileLoader(module.__name__, module.__file__)
        module = loader.load_module()
        timeline_class: type[Timeline] = getattr(module, self.anim.timeline.__class__.__name__)

        try:
            self.anim: TimelineAnim = timeline_class().build()
        except Exception as e:
            if not isinstance(e, ExitException):
                traceback.print_exc()
            log.error('重新构建失败')
            return

        if self.socket is not None:
            msg = json.dumps(dict(
                janim=dict(
                    type='rebuilt'
                )
            ))
            for client in self.clients:
                self.socket.writeDatagram(
                    QByteArray.fromStdString(msg),
                    *client
                )

            time = self.timeline_view.progress_to_time(self.timeline_view.progress())
            self.send_lineno(self.anim.timeline.get_lineno_at_time(time))

        self.setup_audio_player()
        self.play_timer.duration = 1 / self.anim.cfg.preview_fps
        progress = int(progress * self.anim.cfg.preview_fps / preview_fps)

        self.anim.anim_on(self.timeline_view.progress_to_time(progress))

        self.fixed_ratio_widget.set_src_size((self.anim.cfg.pixel_width,
                                              self.anim.cfg.pixel_height))

        self.glw.anim = self.anim
        self.glw.update_clear_color()
        self.glw.update()

        range = self.timeline_view.range
        self.timeline_view.set_anim(self.anim)
        self.timeline_view.set_progress(progress)
        self.timeline_view.range = range

    def on_select_triggered(self) -> None:
        if self.selector is None:
            self.selector = Selector(self)
            self.selector.destroyed.connect(self.on_selector_destroyed)
        else:
            self.selector.clear()

    def on_selector_destroyed(self) -> None:
        self.selector = None

    def on_richtext_edit_triggered(self) -> None:
        if self.richtext_editor is None:
            self.richtext_editor = RichTextEditor(self)
            self.richtext_editor.setWindowFlag(Qt.WindowType.Tool)
            self.richtext_editor.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.richtext_editor.destroyed.connect(self.on_richtext_editor_destroyed)
        self.richtext_editor.show()

    def on_richtext_editor_destroyed(self) -> None:
        self.richtext_editor = None

    def on_glw_rendered(self) -> None:
        cur = time.time()
        self.fps_counter += 1
        if cur - self.fps_record_start >= 1:
            self.fps_label.setText(f'Preview FPS: {self.fps_counter}/{self.anim.cfg.preview_fps}')
            self.fps_counter = 0
            self.fps_record_start = cur

    def on_export_clicked(self) -> None:
        self.play_timer.stop()

        relative_path = os.path.dirname(inspect.getfile(self.anim.timeline.__class__))

        output_dir = self.anim.cfg.formated_output_dir(relative_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        file_path = QFileDialog.getSaveFileName(
            self,
            '',
            os.path.join(output_dir, f'{self.anim.timeline.__class__.__name__}.mp4'),
            'MP4 (*.mp4);;MOV (*.mov)'
        )
        file_path = file_path[0]
        if not file_path:
            return

        QMessageBox.information(self, '提示', '即将进行输出，请留意控制台信息')
        try:
            VideoWriter.writes(self.anim.timeline.__class__().build(), file_path)
        except Exception as e:
            if not isinstance(e, ExitException):
                traceback.print_exc()
        else:
            QMessageBox.information(self, '提示', f'已完成输出至 {file_path}')

    # endregion

    # region play_state

    def set_play_state(self, playing: bool) -> None:
        if playing != self.play_timer.isActive():
            self.switch_play_state()

    def switch_play_state(self) -> None:
        if self.play_timer.isActive():
            self.play_timer.stop()
        else:
            if self.timeline_view.at_end():
                self.timeline_view.set_progress(0)
            self.fps_record_start = time.time()
            self.fps_counter = 0
            self.play_timer.start_precise_timer()

    # endregion

    @classmethod
    def views(cls, anim: TimelineAnim) -> None:
        '''
        直接显示一个浏览构建完成的时间轴动画的窗口
        '''
        app = Application.instance()
        if app is None:
            app = Application()

        w = cls(anim)
        w.show()

        app.exec()


class TimelineView(QWidget):
    '''
    窗口下方的进度条和动画区段指示器

    - **w** 键放大区段（使视野精确到一小段中）
    - **s** 键缩小区段（使视野扩展到一大段中）
    - **a** 和 **d** 左右移动区段
    '''
    @dataclass
    class LabelInfo:
        '''
        动画区段被渲染到第几行的标记
        '''
        anim: Animation
        row: int

    @dataclass
    class PixelRange:
        left: float
        width: float

        @property
        def right(self) -> float:
            return self.left + self.width

    @dataclass
    class Pressing:
        '''
        记录按键状态
        '''
        w: bool = False
        a: bool = False
        s: bool = False
        d: bool = False

    value_changed = Signal(float)
    dragged = Signal()

    space_pressed = Signal()

    # px
    audio_height = 20
    label_height = 24
    range_tip_height = 4
    play_space = 20

    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None):
        super().__init__(parent)

        self.set_anim(anim)

        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.on_hover_timer_timeout)

        self.tooltip: QWidget | None = None

        self.key_timer = QTimer(self)
        self.key_timer.timeout.connect(self.on_key_timer_timeout)
        self.key_timer.start(1000 // 60)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumHeight(self.label_height + self.range_tip_height + 10)

    def set_anim(self, anim: TimelineAnim) -> None:
        self.range = TimeRange(0, min(20, anim.global_range.duration))
        self.y_offset = 0
        self.anim = anim
        self._progress = 0
        self._maximum = round(anim.global_range.end * self.anim.cfg.preview_fps)

        self.is_pressing = TimelineView.Pressing()

        self.init_label_info()
        self.update()

    def init_label_info(self) -> None:
        '''
        计算各个动画区段应当被渲染到第几行，以叠放式进行显示
        '''
        self.labels_info: list[TimelineView.LabelInfo] = []
        self.max_row = 0

        self.flatten = self.anim.user_anim.flatten()[1:]
        self._sorted_anims = None

        stack: list[Animation] = []
        for anim in self.get_sorted_anims():
            # 可能会因为浮点误差导致 <= 中的相等判断错误，所以 +1e-5
            while stack and stack[-1].global_range.end <= anim.global_range.at + 1e-5:
                stack.pop()

            self.labels_info.append(TimelineView.LabelInfo(anim, len(stack)))
            self.max_row = max(self.max_row, len(stack))
            stack.append(anim)

    def get_sorted_anims(self) -> list[Animation]:
        if self._sorted_anims is None:
            self._sorted_anims = sorted(self.flatten, key=lambda x: x.global_range.at)
        return self._sorted_anims

    def set_range(self, at: float, duration: float) -> None:
        duration = min(duration, self.anim.global_range.duration)
        at = clip(at, 0, self.anim.global_range.duration - duration)
        self.range = TimeRange(at, duration)
        self.update()

    def hover_at(self, pos: QPoint) -> None:
        audio_rect = self.audio_rect
        bottom_rect = self.bottom_rect

        # 因为后出现的音频在绘制时会覆盖前面的音频，所以这里用 reversed，就会得到最上层的
        for info in reversed(self.anim.timeline.audio_infos):
            range = self.time_range_to_pixel_range(info.range)
            if QRectF(range.left, audio_rect.y(), range.width, self.audio_height).contains(pos):
                self.hover_at_audio(pos, info)
                return

        for info in self.labels_info:
            range = self.time_range_to_pixel_range(info.anim.global_range)
            if QRectF(range.left,
                      bottom_rect.y() + self.label_y(info.row),
                      range.width,
                      self.label_height).contains(pos):
                self.hover_at_anim(pos, info.anim)

    def hover_at_audio(self, pos: QPoint, info: Timeline.PlayAudioInfo) -> None:
        msg_lst = [
            f'{round(info.range.at, 2)}s ~ {round(info.range.end, 2)}s',
            info.audio.file_path
        ]
        if info.clip_range != TimeRange(0, info.audio.duration()):
            msg_lst.append(f'Clip: {round(info.clip_range.at, 2)}s ~ {round(info.clip_range.end, 2)}s')

        clips = ', '.join(
            f'{math.floor(start * 10) / 10}s ~ {math.ceil(end * 10) / 10}s'
            for start, end in info.audio.recommended_ranges()
        )
        if clips:
            msg_lst.append(f'Recommended clip: {clips}')

        label = QLabel('\n'.join(msg_lst))
        chart_view = self.create_audio_chart(info, near=round(self.pixel_to_time(pos.x())))

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(chart_view)

        self.tooltip = QWidget()
        self.tooltip.setWindowFlag(Qt.WindowType.ToolTip)
        self.tooltip.setLayout(layout)
        self.tooltip.adjustSize()

        self.place_tooltip(self.tooltip, pos)
        self.tooltip.show()

    def create_audio_chart(self, info: Timeline.PlayAudioInfo, near: float | None = None) -> 'QChartView':
        from PySide6.QtCharts import (QChart, QChartView, QLineSeries,
                                      QValueAxis)

        audio = info.audio

        clip_begin = info.clip_range.at
        clip_end = info.clip_range.end
        if near is not None:
            clip_begin = max(clip_begin, near - info.range.at - 4)
            clip_end = min(clip_end, near - info.range.at + 4)

        range_begin = info.range.at + (clip_begin - info.clip_range.at)
        range_end = range_begin + (clip_end - clip_begin)

        begin = int(clip_begin * audio.framerate)
        end = int(clip_end * audio.framerate)

        left_blank = max(0, -begin)
        right_blank = max(0, end - audio.sample_count())

        data = audio._samples.data[max(0, begin): min(end, audio.sample_count())]

        if left_blank != 0 or right_blank != 0:
            data = np.concatenate([
                np.zeros(left_blank, dtype=np.int16),
                data,
                np.zeros(right_blank, dtype=np.int16)
            ])

        unit = audio.framerate // self.anim.cfg.fps

        data: np.ndarray = np.max(
            np.abs(
                data[:len(data) // unit * unit].reshape(-1, unit)
            ),
            axis=1
        ) / np.iinfo(np.int16).max

        times = np.linspace(range_begin,
                            range_end,
                            len(data))

        chart = QChart()

        x_axis = QValueAxis()
        x_axis.setRange(range_begin, range_end)
        x_axis.setTickCount(max(2, 1 + int(range_end - range_begin)))
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)

        y_axis = QValueAxis()
        y_axis.setRange(0, 1)
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)

        x_clip_axis = QValueAxis()
        x_clip_axis.setRange(clip_begin, clip_end)
        chart.addAxis(x_clip_axis, Qt.AlignmentFlag.AlignBottom)

        series = QLineSeries()
        for t, y in zip(times, data):
            series.append(t, y)
        chart.addSeries(series)
        series.attachAxis(x_axis)
        series.attachAxis(y_axis)

        if clip_begin != info.clip_range.at:
            area = self.create_axvspan(clip_begin, interpolate(clip_begin, clip_end, 0.1),
                                       QColor(41, 171, 202, 128), QColor(41, 171, 202, 0))
            chart.addSeries(area)
            area.attachAxis(x_clip_axis)
            area.attachAxis(y_axis)

        if clip_end != info.clip_range.end:
            area = self.create_axvspan(interpolate(clip_begin, clip_end, 0.9), clip_end,
                                       QColor(41, 171, 202, 0), QColor(41, 171, 202, 128))
            chart.addSeries(area)
            area.attachAxis(x_clip_axis)
            area.attachAxis(y_axis)

        chart.legend().setVisible(False)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumSize(350, 200)

        return chart_view

    @staticmethod
    def create_axvspan(x1: float, x2: float, c1: QColor, c2: QColor) -> 'QAreaSeries':
        from PySide6.QtCharts import QAreaSeries, QLineSeries
        from PySide6.QtGui import QGradient, QLinearGradient

        upper_series = QLineSeries()
        upper_series.append(x1, 1.)
        upper_series.append(x2, 1.)

        lower_series = QLineSeries()
        lower_series.append(x1, 0.)
        lower_series.append(x2, 0.)

        area = QAreaSeries(upper_series, lower_series)
        upper_series.setParent(area)
        lower_series.setParent(area)

        grandient = QLinearGradient(QPoint(0, 0), QPoint(1, 0))
        grandient.setColorAt(0.0, c1)
        grandient.setColorAt(1.0, c2)
        grandient.setCoordinateMode(QGradient.CoordinateMode.ObjectBoundingMode)
        area.setBrush(grandient)
        area.setPen(Qt.PenStyle.NoPen)

        return area

    def hover_at_anim(self, pos: QPoint, anim: Animation) -> None:
        parents = [anim]
        while True:
            last = parents[-1]
            if last.parent is None or last.parent is self.anim.user_anim:
                break
            parents.append(last.parent)

        label1 = QLabel(f'{anim.__class__.__name__} '
                        f'{round(anim.global_range.at, 2)}s ~ {round(anim.global_range.end, 2)}s')
        chart_view = self.create_anim_chart(anim)
        label2 = QLabel(
            '\n↑\n'.join(
                f'{anim.rate_func.__name__} ({anim.__class__.__name__})'
                for anim in parents
            )
        )

        layout = QVBoxLayout()
        layout.addWidget(label1)
        layout.addWidget(chart_view)
        layout.addWidget(label2)

        self.tooltip = QWidget()
        self.tooltip.setWindowFlag(Qt.WindowType.ToolTip)
        self.tooltip.setLayout(layout)
        self.tooltip.adjustSize()

        self.place_tooltip(self.tooltip, pos)
        self.tooltip.show()

    def create_anim_chart(self, anim: Animation) -> 'QChartView':
        from PySide6.QtCharts import QChart, QChartView, QScatterSeries

        count = min(500, int(anim.global_range.duration * self.anim.cfg.fps))
        times = np.linspace(anim.global_range.at,
                            anim.global_range.end,
                            count)

        series = QScatterSeries()
        series.setMarkerSize(3)
        series.setPen(Qt.PenStyle.NoPen)
        for t in times:
            series.append(t, anim.get_alpha_on_global_t(t))

        chart = QChart()
        chart.addSeries(series)
        chart.createDefaultAxes()
        chart.legend().setVisible(False)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumSize(250, 200)

        return chart_view

    def place_tooltip(self, tooltip: QWidget, pos: QPoint) -> None:
        rect = tooltip.screen().availableGeometry()
        global_pos = self.mapToGlobal(pos)
        to = QPoint(global_pos) + QPoint(2, 2)
        if to.x() + tooltip.width() > rect.right():
            to.setX(global_pos.x() - tooltip.width() - 2)
        if to.y() + tooltip.height() > rect.bottom():
            to.setY(global_pos.y() - tooltip.height() - 2)

        tooltip.move(to)

    def hide_tooltip(self) -> None:
        if self.tooltip is not None:
            self.tooltip = None

    def on_hover_timer_timeout(self) -> None:
        pos = self.mapFromGlobal(self.cursor().pos())
        if self.rect().contains(pos):
            self.hover_at(pos)

    def on_key_timer_timeout(self) -> None:
        if self.is_pressing.w:
            cursor_time = self.pixel_to_time(self.mapFromGlobal(self.cursor().pos()).x())

            factor = max(TIMELINE_VIEW_MIN_DURATION / self.range.duration, 0.97)
            self.set_range(
                factor * (self.range.at - cursor_time) + cursor_time,
                self.range.duration * factor
            )

        elif self.is_pressing.s:
            cursor_time = self.pixel_to_time(self.mapFromGlobal(self.cursor().pos()).x())

            factor = min(self.anim.global_range.duration / self.range.duration, 1 / 0.97)
            self.set_range(
                factor * (self.range.at - cursor_time) + cursor_time,
                self.range.duration * factor
            )

        if self.is_pressing.a or self.is_pressing.d:
            shift = self.range.duration * 0.05 * (self.is_pressing.d - self.is_pressing.a)
            self.set_range(
                self.range.at + shift,
                self.range.duration
            )

            self.update()

    def set_progress(self, progress: int) -> None:
        progress = clip(progress, 0, self._maximum)
        if progress != self._progress:
            self._progress = progress

            pixel_at = self.progress_to_pixel(progress)
            minimum = self.play_space
            maximum = self.width() - self.play_space
            if pixel_at < minimum:
                self.set_range(
                    self.pixel_to_time(pixel_at - minimum),
                    self.range.duration
                )
            if pixel_at > maximum:
                self.set_range(
                    self.pixel_to_time(pixel_at - maximum),
                    self.range.duration
                )

            self.value_changed.emit(progress)
            self.update()

    def progress(self) -> int:
        return self._progress

    def at_end(self) -> bool:
        return self._progress == self._maximum

    def progress_to_time(self, progress: int) -> float:
        return progress / self.anim.cfg.preview_fps

    def time_to_progress(self, time: float) -> int:
        return round(time * self.anim.cfg.preview_fps)

    def time_to_pixel(self, time: float) -> float:
        return (time - self.range.at) / self.range.duration * self.width()

    def pixel_to_time(self, pixel: float) -> float:
        return pixel / self.width() * self.range.duration + self.range.at

    def progress_to_pixel(self, progress: int) -> float:
        return self.time_to_pixel(self.progress_to_time(progress))

    def pixel_to_progress(self, pixel: float) -> int:
        return self.time_to_progress(self.pixel_to_time(pixel))

    def time_range_to_pixel_range(self, range: TimeRange) -> PixelRange:
        left = (range.at - self.range.at) / self.range.duration * self.width()
        width = range.duration / self.range.duration * self.width()
        return TimelineView.PixelRange(left, width)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_progress(self.pixel_to_progress(event.position().x()))
            self.dragged.emit()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self.hover_timer.start(500)
        self.hide_tooltip()

        if event.buttons() & Qt.MouseButton.LeftButton:
            self.set_progress(self.pixel_to_progress(event.position().x()))
            self.dragged.emit()

    def leaveEvent(self, _) -> None:
        self.hide_tooltip()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        if key == Qt.Key.Key_Space:
            self.space_pressed.emit()

        elif key == Qt.Key.Key_W:
            self.is_pressing.w = True
        elif key == Qt.Key.Key_A:
            self.is_pressing.a = True
        elif key == Qt.Key.Key_S:
            self.is_pressing.s = True
        elif key == Qt.Key.Key_D:
            self.is_pressing.d = True

        elif key == Qt.Key.Key_Z:
            anims = self.get_sorted_anims()
            time = self.progress_to_time(self._progress)
            idx = bisect(anims, time - 1e-2, key=lambda x: x.global_range.at)
            idx -= 1
            if idx < 0:
                self.set_progress(0)
            else:
                self.set_progress(self.time_to_progress(anims[idx].global_range.at))

            self.dragged.emit()

        elif key == Qt.Key.Key_C:
            anims = self.get_sorted_anims()
            time = self.progress_to_time(self._progress)
            idx = bisect(anims, time + 1e-2, key=lambda x: x.global_range.at)
            if idx < len(anims):
                self.set_progress(self.time_to_progress(anims[idx].global_range.at))
            else:
                self.set_progress(self.time_to_progress(self.anim.global_range.end))

            self.dragged.emit()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        if key == Qt.Key.Key_W:
            self.is_pressing.w = False
        elif key == Qt.Key.Key_A:
            self.is_pressing.a = False
        elif key == Qt.Key.Key_S:
            self.is_pressing.s = False
        elif key == Qt.Key.Key_D:
            self.is_pressing.d = False

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.y_offset = clip(self.y_offset - event.angleDelta().y() / 240 * self.label_height,
                             0,
                             self.max_row * self.label_height)
        self.update()

    def paintEvent(self, _: QPaintEvent) -> None:
        p = QPainter(self)
        orig_font = p.font()

        # 绘制每次 forward 或 play 的时刻
        times_of_code = self.anim.timeline.times_of_code
        left = bisect(times_of_code, self.range.at - 1e-5, key=lambda x: x.time)
        right = bisect(times_of_code, self.range.end + 1e-5, key=lambda x: x.time)

        p.setPen(QPen(QColor(74, 48, 80), 2))
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for time_of_code in times_of_code[left:right]:
            self.paint_line(p, time_of_code.time)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 绘制音频区段
        if self.anim.timeline.has_audio():
            audio_rect = self.audio_rect

            font = p.font()
            font.setPointSize(8)
            p.setFont(font)

            for info in self.anim.timeline.audio_infos:
                if info.range.end <= self.range.at or info.range.at >= self.range.end:
                    continue

                self.paint_label(p,
                                 info.range,
                                 audio_rect.y(),
                                 self.audio_height,
                                 info.audio.filename,
                                 QColor(152, 255, 191),
                                 QColor(152, 255, 191, 128),
                                 False)

            p.setFont(orig_font)

        # 绘制动画区段
        bottom_rect = self.bottom_rect
        p.setClipRect(bottom_rect)

        for info in self.labels_info:
            if info.anim.global_range.end <= self.range.at or info.anim.global_range.at >= self.range.end:
                continue

            self.paint_label(p,
                             info.anim.global_range,
                             bottom_rect.y() + self.label_y(info.row),
                             self.label_height,
                             info.anim.__class__.__name__,
                             Qt.PenStyle.NoPen,
                             QColor(*info.anim.label_color).lighter(),
                             True)

        p.setClipping(False)

        # 绘制当前进度指示
        p.setPen(QPen(Qt.GlobalColor.white, 2))
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.paint_line(p, self.progress_to_time(self._progress))
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 绘制视野区域指示（底部的长条）
        left = self.range.at / self.anim.global_range.duration * self.width()
        width = self.range.duration / self.anim.global_range.duration * self.width()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(77, 102, 132))
        p.drawRoundedRect(
            left,
            self.height() - self.range_tip_height,
            width,
            self.range_tip_height,
            self.range_tip_height / 2,
            self.range_tip_height / 2
        )

    @property
    def audio_rect(self) -> QRect:
        if not self.anim.timeline.has_audio():
            return QRect(0, 0, self.width(), 0)
        return QRect(0, 0, self.width(), self.audio_height)

    @property
    def bottom_rect(self) -> QRect:
        return self.rect().adjusted(0,
                                    self.audio_height if self.anim.timeline.has_audio() else 0,
                                    0,
                                    -self.range_tip_height)

    def label_y(self, row: int) -> float:
        return -self.y_offset + row * self.label_height

    def paint_label(
        self,
        p: QPainter,
        time_range: TimeRange,
        y: float,
        height: float,
        txt: str,
        stroke: QPen | QColor,
        fill: QBrush | QColor,
        is_anim_lable: bool
    ) -> None:
        range = self.time_range_to_pixel_range(time_range)
        rect = QRectF(range.left, y, range.width, height)

        # 标记是否应当绘制文字
        out_of_boundary = False

        if is_anim_lable:
            # 使得超出底端的区段也能看到一条边
            max_y = self.height() - self.range_tip_height - 4
            if rect.y() > max_y:
                rect.moveTop(max_y)
                rect.setHeight(4)
                out_of_boundary = True

            # 使得超出顶端的区段也能看到一条边
            top_margin = self.audio_height if self.anim.timeline.has_audio() else 0
            min_bottom = top_margin + 4
            if rect.bottom() < min_bottom:
                rect.moveTop(top_margin)
                rect.setHeight(4)
                out_of_boundary = True

        # 这里的判断使得区段过窄时也能看得见
        if rect.width() > 5:
            x_adjust = 2
        elif rect.width() > 1:
            x_adjust = (rect.width() - 1) / 2
        else:
            x_adjust = 0

        # 绘制背景部分
        if not out_of_boundary:
            rect.adjust(x_adjust, 2, -x_adjust, -2)
        p.setPen(stroke)
        p.setBrush(fill)
        p.drawRect(rect)

        # 使得在区段的左侧有一部分在显示区域外时，
        # 文字仍然对齐到屏幕的左端，而不是跑到屏幕外面去
        if rect.x() < 0:
            rect.setX(0)

        # 绘制文字
        if not out_of_boundary:
            rect.adjust(1, 1, -1, -1)
            p.setPen(Qt.GlobalColor.black)
            p.drawText(
                rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                txt
            )

    def paint_line(self, p: QPainter, time: float) -> None:
        pixel_at = self.time_to_pixel(time)
        p.drawLine(pixel_at, 0, pixel_at, self.height())
