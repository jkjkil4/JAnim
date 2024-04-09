import importlib.machinery
import inspect
import json
import os
import sys
import time
import traceback
from bisect import bisect
from dataclasses import dataclass

try:
    # flake8: noqa
    import PySide6
except ImportError:
    print('使用 GUI 界面时需要安装额外模块，但是未安装')
    print('你可以使用 pip install janim[gui] 进行安装，并确保你安装在了正确的 Python 版本中')

    from janim.exception import EXITCODE_PYSIDE6_NOT_FOUND, ExitException
    raise ExitException(EXITCODE_PYSIDE6_NOT_FOUND)


from PySide6.QtCore import QByteArray, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QCloseEvent, QColor, QHideEvent, QIcon, QKeyEvent,
                           QMouseEvent, QPainter, QPaintEvent, QPen,
                           QWheelEvent)
from PySide6.QtWidgets import (QApplication, QFileDialog, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QSizePolicy,
                               QSplitter, QStackedLayout, QWidget)

from janim.anims.animation import Animation, TimeRange
from janim.anims.timeline import Timeline, TimelineAnim
from janim.exception import ExitException
from janim.gui.application import Application
from janim.gui.fixed_ratio_widget import FixedRatioWidget
from janim.gui.glwidget import GLWidget
from janim.gui.richtext_editor import RichTextEditor
from janim.gui.selector import Selector
from janim.logger import log
from janim.render.file_writer import FileWriter
from janim.utils.config import Config
from janim.utils.file_ops import get_janim_dir
from janim.utils.simple_functions import clip

TIMELINE_VIEW_MIN_DURATION = 0.5
TIMELINE_VIEW_RANGE_TIP_HEIGHT = 4

# TODO: 鼠标悬停在时间轴的动画上时，显示动画信息


class AnimViewer(QMainWindow):
    '''
    用于显示构建完成的时间轴动画

    可以使用 ``AnimViewer.views(MyTimeline().build())`` 进行直接显示
    '''
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

        self.play_timer = QTimer(self)
        self.play_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.play_timer.timeout.connect(self.on_play_timer_timeout)
        if auto_play:
            self.switch_play_state()

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

        action_stay_on_top = menu_functions.addAction('窗口置前')
        action_stay_on_top.setCheckable(True)
        action_stay_on_top.setShortcut('Ctrl+T')
        action_stay_on_top.toggled.connect(self.on_stay_on_top_toggled)
        action_stay_on_top.setChecked(True)

        menu_functions.addSeparator()

        action_reload = menu_functions.addAction('重新构建')
        action_reload.setShortcut('Ctrl+L')
        action_reload.triggered.connect(self.on_rebuild_triggered)

        menu_functions.addSeparator()

        action_select = menu_functions.addAction('子物件选择')
        action_select.setShortcut('Ctrl+S')
        action_select.triggered.connect(self.on_select_triggered)
        self.selector: Selector | None = None

        action_richtext_edit = menu_functions.addAction('富文本编辑')
        action_richtext_edit.setShortcut('Ctrl+R')
        action_richtext_edit.triggered.connect(self.on_richtext_edit_triggered)
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
            (Config.get.pixel_width, Config.get.pixel_height)
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
        window_position = Config.get.wnd_pos
        window_monitor = Config.get.wnd_monitor

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
        self.timeline_view.set_progress(self.timeline_view.progress() + 1)
        if self.timeline_view.at_end():
            self.play_timer.stop()

    def on_stay_on_top_toggled(self, flag: bool) -> None:
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, flag)
        if visible:
            self.setVisible(True)

    def on_rebuild_triggered(self) -> None:
        module = inspect.getmodule(self.anim.timeline)
        progress = self.timeline_view.progress()

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

        self.anim.anim_on(self.timeline_view.progress_to_time(progress))

        self.glw.anim = self.anim
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
            self.fps_label.setText(f'Preview FPS: {self.fps_counter}/{Config.get.preview_fps}')
            self.fps_counter = 0
            self.fps_record_start = cur

    def on_export_clicked(self) -> None:
        self.play_timer.stop()

        output_dir = Config.get.output_dir
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
            FileWriter.writes(self.anim.timeline.__class__().build(), file_path)
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
            self.play_timer.start(1000 // Config.get.preview_fps)

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

    label_height = 24   # px
    play_space = 20     # px

    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None):
        super().__init__(parent)

        self.set_anim(anim)

        self.key_timer = QTimer(self)
        self.key_timer.timeout.connect(self.on_key_timer_timeout)
        self.key_timer.start(1000 // 60)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def set_anim(self, anim: TimelineAnim) -> None:
        self.range = TimeRange(0, min(20, anim.global_range.duration))
        self.y_offset = 0
        self.anim = anim
        self._progress = 0
        self._maximum = round(anim.global_range.end * Config.get.preview_fps)

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
        for anim in self.flatten:
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

    def set_progress(self, progress: float) -> None:
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
        return progress / Config.get.preview_fps

    def time_to_progress(self, time: float) -> int:
        return round(time * Config.get.preview_fps)

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
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.set_progress(self.pixel_to_progress(event.position().x()))
            self.dragged.emit()

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
            idx = bisect(anims, time - 1e-5, key=lambda x: x.global_range.at)
            idx -= 1
            if idx < 0:
                self.set_progress(0)
            else:
                self.set_progress(self.time_to_progress(anims[idx].global_range.at))

            self.dragged.emit()

        elif key == Qt.Key.Key_C:
            anims = self.get_sorted_anims()
            time = self.progress_to_time(self._progress)
            idx = bisect(anims, time + 1e-5, key=lambda x: x.global_range.at)
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

        # 绘制动画区段
        for info in self.labels_info:
            if info.anim.global_range.end <= self.range.at or info.anim.global_range.at >= self.range.end:
                continue

            range = self.time_range_to_pixel_range(info.anim.global_range)
            rect = QRectF(range.left, -self.y_offset + info.row * self.label_height, range.width, self.label_height)

            # 标记是否应当绘制名称
            draw_text = True

            # 使得在区段的左侧有一部分在显示区域外时，
            # 文字仍然对齐到屏幕的左端，而不是跑到屏幕外面去
            if rect.x() < 0:
                rect.setX(0)

            # 使得过于下面的区段也能看到一条边
            max_y = self.height() - TIMELINE_VIEW_RANGE_TIP_HEIGHT - 4
            if rect.y() > max_y:
                rect.setY(max_y)
                rect.setBottom(self.height() + 2)
                draw_text = False

            # 这里的判断使得区段过窄时也能看得见
            if rect.width() > 5:
                x_adjust = 2
            elif rect.width() > 1:
                x_adjust = (rect.width() - 1) / 2
            else:
                x_adjust = 0

            # 绘制背景部分
            rect.adjust(x_adjust, 2, -x_adjust, -2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(*info.anim.label_color).lighter())
            p.drawRect(rect)

            if not draw_text:
                continue

            # 绘制动画类名
            rect.adjust(1, 1, -1, -1)
            p.setPen(Qt.GlobalColor.black)
            p.drawText(
                rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                f'{info.anim.__class__.__name__}'
            )

        # 绘制当前进度指示
        pixel_at = self.progress_to_pixel(self._progress)
        p.setPen(QPen(Qt.GlobalColor.white, 2))
        p.drawLine(pixel_at, 0, pixel_at, self.height())

        # 绘制视野区域指示（底部的长条）
        left = self.range.at / self.anim.global_range.duration * self.width()
        width = self.range.duration / self.anim.global_range.duration * self.width()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(77, 102, 132))
        p.drawRoundedRect(
            left,
            self.height() - TIMELINE_VIEW_RANGE_TIP_HEIGHT,
            width,
            TIMELINE_VIEW_RANGE_TIP_HEIGHT,
            TIMELINE_VIEW_RANGE_TIP_HEIGHT / 2,
            TIMELINE_VIEW_RANGE_TIP_HEIGHT / 2
        )

        # TODO: 对连续两次 forward 中间添加标记
        # 因为连续两次 forward 很可能进行了非动画的更改，
        # 对此进行标记有利于直观看出这个变化出现的位置
