try:
    import PySide6  # noqa: F401
except ImportError:
    from janim.locale.i18n import get_local_strings
    _ = get_local_strings('anim_viewer')

    print(_('Additional modules need to be installed when using the GUI interface, but they are not installed'))
    print(_('You can install them using pip install "janim[gui]" '
            'and make sure you install them in the correct Python version'))

    from janim.exception import EXITCODE_PYSIDE6_NOT_FOUND, ExitException
    raise ExitException(EXITCODE_PYSIDE6_NOT_FOUND)

import importlib.machinery
import inspect
import json
import os
import sys
import time
import traceback
from bisect import bisect_right
from contextlib import contextmanager, nullcontext

from PySide6.QtCore import (QByteArray, QEvent, QPoint, QSettings, Qt, QTimer,
                            Signal)
from PySide6.QtGui import (QAction, QCloseEvent, QGuiApplication, QHideEvent,
                           QIcon, QShowEvent)
from PySide6.QtWidgets import (QApplication, QCompleter, QLabel, QLineEdit,
                               QMainWindow, QMessageBox, QPushButton,
                               QSizePolicy, QSplitter, QStackedLayout, QWidget)

from janim.anims.timeline import BuiltTimeline, Timeline
from janim.exception import ExitException
from janim.gui.application import Application
from janim.gui.audio_player import AudioPlayer
from janim.gui.fixed_ratio_widget import FixedRatioWidget
from janim.gui.functions.capture_dialog import CaptureDialog
from janim.gui.functions.color_widget import ColorWidget
from janim.gui.functions.export_dialog import ExportDialog
from janim.gui.functions.font_table import FontTable
from janim.gui.functions.painter import Painter
from janim.gui.functions.richtext_editor import RichTextEditor
from janim.gui.functions.selector import Selector
from janim.gui.glwidget import GLWidget
from janim.gui.precise_timer import PreciseTimer
from janim.gui.timeline_view import TimelineView
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.writer import AudioWriter, VideoWriter, merge_video_and_audio
from janim.utils.config import Config, cli_config
from janim.utils.file_ops import get_janim_dir, getfile_or_empty, open_file
from janim.utils.reload import reset_reloads_state

_ = get_local_strings('anim_viewer')

ACTION_WIDGET_FLAG_KEY = '__action_widget'


class AnimViewer(QMainWindow):
    '''
    用于显示构建完成的时间轴动画

    可以使用 ``AnimViewer.views(MyTimeline().build())`` 进行直接显示
    '''
    play_finished = Signal()

    def __init__(
        self,
        built: BuiltTimeline,
        *,
        auto_play: bool = True,
        interact: bool = False,
        available_timeline_names: list[str] | None = None,
        parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.code_file_path = getfile_or_empty(built.timeline.__class__)

        self.setup_ui()
        self.setup_play_timer()
        if interact:
            self.setup_socket(built.cfg.client_search_port)
        else:
            self.socket = None
        self.audio_player = None

        self.setup_slots()

        self.set_built(built)

        self.timeline_view.value_changed.emit(0)
        self.action_stay_on_top.setChecked(True)

        if auto_play:
            self.switch_play_state()
        self.playback_stopped: bool = False

        if available_timeline_names is not None:
            self.update_completer(available_timeline_names)

    @classmethod
    def views(cls, anim: BuiltTimeline, **kwargs) -> None:
        '''
        直接显示一个浏览构建完成的时间轴动画的窗口
        '''
        app = Application.instance()
        if app is None:
            app = Application()

        w = cls(anim, **kwargs)
        w.show()

        app.exec()

    def set_built(self, built: BuiltTimeline) -> None:
        self.built = built

        # data
        def to_progress(p: Timeline.PausePoint) -> int:
            rough_progress = p.at * self.built.cfg.preview_fps

            if rough_progress % 1 < 1e-3:
                result = int(rough_progress)
            else:
                result = int(rough_progress) + 1

            if p.at_previous_frame:
                result -= 1

            return result

        self.pause_progresses = list(map(to_progress, built.timeline.pause_points))
        self.pause_progresses.sort()

        # menu bar
        if self.selector is not None:
            self.selector.deleteLater()

        # central widget
        self.fixed_ratio_widget.set_src_size((built.cfg.pixel_width, built.cfg.pixel_height))
        self.glw.set_built(built)
        self.timeline_view.set_built(built, self.pause_progresses)

        # status bar
        self.name_edit.setText(built.timeline.__class__.__name__)

        # other
        self.play_timer.set_duration(1 / built.cfg.preview_fps)
        if self.play_timer.isActive():
            self.play_timer.start_precise_timer()
        if self.play_timer.skip_enabled:
            self.play_timer.take_skip_count()

        if self.built.timeline.has_audio_for_all() and self.audio_player is None:
            self.audio_player = AudioPlayer(self.built.cfg.audio_framerate,
                                            self.built.cfg.audio_channels,
                                            self.built.cfg.preview_fps)

    # region setup_ui

    def setup_ui(self) -> None:
        self.moved_to_position = False

        self.setup_menu_bar()
        self.setup_status_bar()
        self.setup_central_widget()

        self.setMinimumSize(200, 160)
        self.resize(800, 608)
        self.setWindowTitle('JAnim Graphics')
        self.setWindowIcon(QIcon(os.path.join(get_janim_dir(), 'gui', 'favicon.ico')))
        self.setWindowFlags(Qt.WindowType.Window)
        self.timeline_view.setFocus()

        self.load_options()

        # 在 macOS 中，设置了 WindowStaysOnTopHint 后，点击窗口会把 Tool 窗口遮挡
        # 所以这里监听窗口事件，只要点击了窗口，就手动把 Tool 窗口放到最上面
        if sys.platform == "darwin":
            QApplication.instance().installEventFilter(self)

    def setup_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        menu_file = menu_bar.addMenu(_('File(&F)'))

        self.action_rebuild = menu_file.addAction(_('Rebuild(&L)'))
        self.action_rebuild.setShortcut('Ctrl+L')
        self.action_rebuild.setAutoRepeat(False)

        menu_file.addSeparator()

        self.action_export = menu_file.addAction(_('Export(&E)'))
        self.action_export.setShortcut('Ctrl+S')
        self.action_export.setAutoRepeat(False)

        self.action_capture = menu_file.addAction(_('Capture(&C)'))
        self.action_capture.setShortcut('Ctrl+Alt+S')
        self.action_capture.setAutoRepeat(False)

        menu_file.addSeparator()

        self.action_set_in_point = menu_file.addAction(_('Set In Point(&I)'))
        self.action_set_in_point.setShortcut('[')
        self.action_set_in_point.setAutoRepeat(False)

        self.action_set_out_point = menu_file.addAction(_('Set Out Point(&O)'))
        self.action_set_out_point.setShortcut(']')
        self.action_set_out_point.setAutoRepeat(False)

        self.action_reset_inout_point = menu_file.addAction(_('Reset In/Out Point(&R)'))
        self.action_reset_inout_point.setAutoRepeat(False)

        menu_view = menu_bar.addMenu(_('View(&V)'))

        self.action_stay_on_top = menu_view.addAction(_('Stay on top(&T)'))
        self.action_stay_on_top.setCheckable(True)
        self.action_stay_on_top.setShortcut('Ctrl+T')
        self.action_stay_on_top.setAutoRepeat(False)

        self.action_frame_skip = menu_view.addAction(_('Frame skip(&P)'))
        self.action_frame_skip.setCheckable(True)
        self.action_frame_skip.setShortcut('Ctrl+P')
        self.action_frame_skip.setAutoRepeat(False)

        menu_tools = menu_bar.addMenu(_('Tools(&T)'))

        self.action_select = menu_tools.addAction(_('Subitem selector(&I)'))
        self.action_select.setShortcut('Ctrl+I')
        self.action_select.setAutoRepeat(False)
        self.selector: Selector | None = None

        self.action_painter = menu_tools.addAction(_('Draw(&D)'))
        self.action_painter.setShortcut('Ctrl+D')
        self.action_painter.setAutoRepeat(False)

        self.action_richtext_edit = menu_tools.addAction(_('Rich text editor(&R)'))
        self.action_richtext_edit.setShortcut('Ctrl+R')
        self.action_richtext_edit.setAutoRepeat(False)

        self.action_font_table = menu_tools.addAction(_('Font list(&F)'))
        self.action_font_table.setShortcut('Ctrl+F')
        self.action_font_table.setAutoRepeat(False)

        self.action_color_widget = menu_tools.addAction(_('Color(&O)'))
        self.action_color_widget.setShortcut('Ctrl+O')
        self.action_color_widget.setAutoRepeat(False)

        menu_tools.addSeparator()

        self.action_copy_time = menu_tools.addAction(_('Copy time point(&T)'))
        self.action_copy_time.setShortcut('T')
        self.action_copy_time.setAutoRepeat(False)

    def setup_status_bar(self) -> None:
        self.fps_label = QLabel()
        self.time_label = QPushButton()
        self.name_edit = QLineEdit()

        self.btn_capture = QPushButton()
        self.btn_capture.setIcon(QIcon(os.path.join(get_janim_dir(), 'gui', 'capture.png')))
        self.btn_capture.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.btn_export = QPushButton()
        self.btn_export.setIcon(QIcon(os.path.join(get_janim_dir(), 'gui', 'export.png')))
        self.btn_export.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        stb = self.statusBar()
        stb.setFixedHeight(stb.height())
        stb.setContentsMargins(0, 0, 0, 0)
        stb.addWidget(self.fps_label)
        stb.addPermanentWidget(self.name_edit)
        stb.addPermanentWidget(self.time_label)
        stb.addPermanentWidget(self.btn_capture)
        stb.addPermanentWidget(self.btn_export)

    def setup_central_widget(self) -> None:
        self.glw = GLWidget(self)
        self.glw.setMouseTracking(True)

        self.overlay = QWidget(self)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.stkLayout = QStackedLayout()
        self.stkLayout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.stkLayout.addWidget(self.glw)
        self.stkLayout.addWidget(self.overlay)

        self.stkWidget = QWidget(self)
        self.stkWidget.setLayout(self.stkLayout)

        self.fixed_ratio_widget = FixedRatioWidget(self.stkWidget)

        self.timeline_view = TimelineView()
        self.timeline_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.vsplitter = QSplitter()
        self.vsplitter.setOrientation(Qt.Orientation.Vertical)
        self.vsplitter.addWidget(self.fixed_ratio_widget)
        self.vsplitter.addWidget(self.timeline_view)
        self.vsplitter.setSizes([400, 100])
        self.vsplitter.setStyleSheet('QSplitter { background: rgb(25, 35, 45); }')
        self.setCentralWidget(self.vsplitter)

    def move_to_position(self) -> None:
        window_position = self.built.cfg.wnd_pos
        window_monitor = self.built.cfg.wnd_monitor

        if len(window_position) != 2 or window_position[0] not in 'UOD' or window_position[1] not in 'LOR':
            log.warning(
                _('wnd_pos has wrong argument {wnd_pos}.')
                .format(wnd_pos=window_position)
            )
            window_position = 'UR'

        screens = QApplication.screens()
        if window_monitor < len(screens):
            screen = screens[window_monitor]
        else:
            screen = screens[0]
            log.warning(
                _('wnd_monitor has invalid value {wnd_monitor}, use {range} instead.')
                .format(wnd_monitor=window_monitor,
                        range=('0' if len(screens) == 1 else f'0~{len(screens) - 1}'))
            )
        geometry = screen.availableGeometry()

        if window_position[1] != 'O':
            if window_position[1] == 'L':
                geometry.adjust(0, 0, -geometry.width() // 2, 0)
            else:
                geometry.adjust(geometry.width() // 2, 0, 0, 0)

        if window_position[0] != 'O':
            if window_position[0] == 'U':
                geometry.adjust(0, 0, 0, -geometry.height() // 2)
            else:
                geometry.adjust(0, geometry.height() // 2, 0, 0)

        margins = self.windowHandle().frameMargins()
        geometry.adjust(margins.left(), margins.top(), margins.right(), margins.bottom())

        self.windowHandle().setScreen(screen)   # 在 Windows 中不需要这句也行，但是 macOS 中需要这句才能正确移动到副屏
        self.setGeometry(geometry)

    def update_completer(self, completions: list[str]) -> None:
        completer = QCompleter(completions)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_edit.setCompleter(completer)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self.moved_to_position:
            self.move_to_position()
            self.moved_to_position = True

    # endregion (setup_ui)

    # region options

    def load_options(self) -> None:
        settings = QSettings(os.path.join(Config.get.temp_dir, 'anim_viewer.ini'), QSettings.Format.IniFormat)
        settings.beginGroup(self.code_file_path)
        frame_skip = settings.value('frame_skip', False, type=bool)
        settings.endGroup()

        self.action_frame_skip.setChecked(frame_skip)
        if frame_skip:
            # 在渲染后才真正启用 frame_skip，避免启动时跳过太多帧
            def slot() -> None:
                self.play_timer.start_precise_timer()   # 重置时间
                self.play_timer.set_skip_enabled(True)
                self.glw.rendered.disconnect(slot)

            self.glw.rendered.connect(slot)

    def save_options(self) -> None:
        settings = QSettings(os.path.join(Config.get.temp_dir, 'anim_viewer.ini'), QSettings.Format.IniFormat)
        settings.beginGroup(self.code_file_path)
        settings.setValue('frame_skip', self.action_frame_skip.isChecked())
        settings.endGroup()

    # endregion

    # region play_timer

    def setup_play_timer(self) -> None:
        self.play_timer = PreciseTimer(parent=self)

        self.fps_counter = 0
        self.fps_prev = 0
        self.fps_record_start = time.time()

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

    def hideEvent(self, event: QHideEvent) -> None:
        super().hideEvent(event)
        self.play_timer.stop()

    # endregion (play_timer)

    # region slots

    def setup_slots(self) -> None:
        self.action_rebuild.triggered.connect(self.on_rebuild_triggered)
        self.action_export.triggered.connect(self.on_export_clicked)
        self.action_capture.triggered.connect(self.on_capture_clicked)
        self.action_set_in_point.triggered.connect(self.timeline_view.set_in_point)
        self.action_set_out_point.triggered.connect(self.timeline_view.set_out_point)
        self.action_reset_inout_point.triggered.connect(self.timeline_view.reset_inout_point)
        self.action_stay_on_top.toggled.connect(self.on_stay_on_top_toggled)
        self.action_frame_skip.toggled.connect(self.on_frame_skip_toggled)
        self.action_select.triggered.connect(self.on_select_triggered)
        self.connect_action_widget(self.action_painter, Painter)
        self.connect_action_widget(self.action_richtext_edit, RichTextEditor)
        self.connect_action_widget(self.action_font_table, FontTable)
        self.connect_action_widget(self.action_color_widget, ColorWidget)
        self.action_copy_time.triggered.connect(self.on_copy_time_triggered)

        self.timeline_view.value_changed.connect(self.on_value_changed)
        self.timeline_view.dragged.connect(lambda: self.set_play_state(False))
        self.timeline_view.space_pressed.connect(lambda: self.switch_play_state())

        self.play_timer.timeout.connect(self.on_play_timer_timeout)
        self.glw.rendered.connect(self.on_glw_rendered)
        self.glw.error_occurred.connect(self.on_error_occurred)
        self.name_edit.editingFinished.connect(self.on_name_edit_finished)
        self.time_label.clicked.connect(self.on_copy_time_triggered)
        self.btn_capture.clicked.connect(self.on_capture_clicked)
        self.btn_export.clicked.connect(self.on_export_clicked)

    # region slots-menu

    def on_stay_on_top_toggled(self, flag: bool) -> None:
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, flag)
        if visible:
            self.setVisible(True)

    def on_frame_skip_toggled(self, flag: bool) -> None:
        self.play_timer.set_skip_enabled(flag)
        self.update_fps_label()

    def on_rebuild_triggered(self) -> None:
        module = inspect.getmodule(self.built.timeline)
        progress = self.timeline_view.progress()
        preview_fps = self.built.cfg.preview_fps

        name = self.name_edit.text().strip()
        stay_same = self.built.timeline.__class__.__name__ == name

        module_name = module.__name__
        # If the AnimViewer is run by executing
        #
        # if __name__ == '__main__':
        #     AnimViewer.views(YourTimeline().build())
        #
        # directly,
        # this condition might be triggered during rebuilding.
        #
        # To avoid this, I change the module name to '__janim_main__'.
        if module_name == '__main__':
            module_name = '__janim_main__'

        reset_reloads_state()
        loader = importlib.machinery.SourceFileLoader(module_name, module.__file__)
        module = loader.load_module()
        timeline_class = getattr(module, name, None)
        if not isinstance(timeline_class, type) or not issubclass(timeline_class, Timeline):
            log.error(
                _('No timeline named "{name}" in "{file}"')
                .format(name=name, file=module.__file__)
            )
            return

        try:
            built: BuiltTimeline = timeline_class().build(
                hide_subtitles=self.built.timeline.hide_subtitles,
                show_debug_notice=True
            )
        except Exception as e:
            if not isinstance(e, ExitException):
                traceback.print_exc()
            log.error(_('Failed to rebuild'))
            return

        range = self.timeline_view.range
        inout_point = self.timeline_view.inout_point

        self.set_built(built)

        if not stay_same:
            # self.set_built 里面调用了 timeline_view.set_built，其中已经将 _progress 置为 0
            # self.timeline_view.set_progress(0)
            self.glw.set_time(0)
        else:
            # 把原来进度（所在第几帧）转换到新的进度
            # 如果帧率没变，则进度不变
            # 如果帧率变了，例如从 30fps 到 60fps，则进度 43 对应 进度 86（乘了 2）
            progress = int(progress * self.built.cfg.preview_fps / preview_fps)
            self.timeline_view.set_progress(progress)

            # 设置 range 是为了保留动画标签的相对位置
            # 比如，本来是 0~1s 和 1~2s 分别一个动画
            # 重新构建后，只剩下了 0~1s 的动画
            # 那么仍保留原来的显示范围，使得 0~1s 的显示位置不变，虽然显示范围超出了持续时间
            self.timeline_view.range = range

            # 设置回 入点/出点 信息，并根据当前的总时长进行调整
            # 后一个判断对应“如果入点比总时长还大，那么就不设置回 入点/出点 信息了”
            if inout_point is not None and inout_point[0] < built.duration:
                self.timeline_view.inout_point = (inout_point[0], min(inout_point[1], built.duration))

        import gc

        from janim.cli import get_all_timelines_from_module

        gc.collect()
        get_all_timelines_from_module.cache_clear()
        self.update_completer([timeline.__name__ for timeline in get_all_timelines_from_module(module)])

        # 向 vscode 客户端发送重新构建了的信息
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
            self.send_lineno(self.built.timeline.get_lineno_at_time(time))

        self.glw.update()

    def on_select_triggered(self) -> None:
        if self.selector is None:
            self.selector = Selector(self)
            self.selector.destroyed.connect(self.on_selector_destroyed)
        else:
            self.selector.clear()

    def on_selector_destroyed(self) -> None:
        self.selector = None

    def connect_action_widget(self, action: QAction, widget_cls: type[QWidget]) -> None:
        widget = None

        def triggered() -> None:
            nonlocal widget
            if widget is None:
                widget = widget_cls(self)
                widget.setWindowFlag(Qt.WindowType.Tool)
                widget.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                widget.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
                widget.destroyed.connect(destroyed)
                if sys.platform == "darwin":
                    setattr(widget, ACTION_WIDGET_FLAG_KEY, True)
            widget.show()

        def destroyed() -> None:
            nonlocal widget
            widget = None

        action.triggered.connect(triggered)

    def on_copy_time_triggered(self) -> None:
        view = self.timeline_view
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(f'{view.progress_to_time(view.progress()):.2f}')

        self.copied_label = QLabel(_('Copied!'))
        self.copied_label.setStyleSheet(
            '''
            background-color: #232629;
            border: 1px solid white;
            padding: 2px 4px;
            border-radius: 6px;
            font-size: 12px;
            '''
        )
        self.copied_label.setWindowFlag(Qt.WindowType.ToolTip)
        self.copied_label.adjustSize()

        pos = QPoint(self.time_label.width() // 2, self.time_label.height() // 2)
        pos = self.time_label.mapToGlobal(pos)
        pos -= QPoint(self.copied_label.width() // 2, self.copied_label.height() // 2)

        self.copied_label.move(pos)
        self.copied_label.show()
        QTimer.singleShot(500, self.copied_label.hide)

    # endregion (slots-menu)

    # region slots-anim

    def on_value_changed(self, value: int) -> None:
        time = self.timeline_view.progress_to_time(value)

        if self.socket is not None:
            line = self.built.timeline.get_lineno_at_time(time)

            if line != self.lineno:
                self.lineno = line

                self.send_lineno(line)

        self.glw.set_time(time)
        self.time_label.setText(f'{time:.1f}/{self.built.duration:.1f} s')

    def on_glw_rendered(self) -> None:
        cur = time.time()
        self.fps_counter += 1
        if cur - self.fps_record_start >= 1:
            self.fps_prev = self.fps_counter
            self.update_fps_label()
            self.fps_counter = 0
            self.fps_record_start = cur

    def on_error_occurred(self) -> None:
        if not self.playback_stopped and self.play_timer.isActive():
            self.play_timer.stop()
            # 这里使用 QTimer.singleShot 是为了让这个消息尽量在 traceback 后再显示
            QTimer.singleShot(
                0,
                lambda: log.error(_('An error occurred during rendering, playback stopped'))
            )

        # 没把这个放在 if 分支里，是为了在 inactive 的时候也设置为 True
        self.playback_stopped = True

    def update_fps_label(self) -> None:
        if self.action_frame_skip.isChecked():
            self.fps_label.setText(f'Preview FPS: {self.fps_prev} ({self.built.cfg.preview_fps})')
        else:
            self.fps_label.setText(f'Preview FPS: {self.fps_prev}/{self.built.cfg.preview_fps}')

    def on_play_timer_timeout(self) -> None:
        played_count = 1 + self.play_timer.take_skip_count()
        prev_progress = self.timeline_view.progress()
        curr_progress = prev_progress + played_count

        # 播放 prev_progress ~ curr_progress 之间的音频
        if self.built.timeline.has_audio_for_all():
            samples = self.built.get_audio_samples_of_frame(self.built.cfg.preview_fps,
                                                            self.built.cfg.audio_framerate,
                                                            prev_progress,
                                                            count=played_count)
            self.audio_player.write(samples.tobytes())

        # 查找 (prev_progress, curr_progress] 的区段的第一个 pause_point，如果有则暂停到特定位置
        if self.pause_progresses:
            # 找到第一个大于 prev_progress 的位置
            idx = bisect_right(self.pause_progresses, prev_progress)
            # 确认这个数是否 <= curr_progress
            if idx < len(self.pause_progresses) and self.pause_progresses[idx] <= curr_progress:
                curr_progress = self.pause_progresses[idx]
                self.play_timer.stop()

        self.timeline_view.set_progress(curr_progress)

        # 如果播放到了结尾则停止 timer
        if self.timeline_view.at_end():
            self.play_finished.emit()
            self.play_timer.stop()

    def on_name_edit_finished(self) -> None:
        if self.name_edit.text().strip() != self.built.timeline.__class__.__name__:
            self.play_timer.stop()
            self.on_rebuild_triggered()
            self.timeline_view.setFocus()

    def on_capture_clicked(self) -> None:
        self.play_timer.stop()

        dialog = CaptureDialog(self.built, self)
        ret = dialog.exec()
        if not ret:
            return

        file_path = dialog.file_path()
        transparent = dialog.transparent()

        ret = False
        t = self.timeline_view.progress_to_time(self.timeline_view.progress())
        try:
            with self.change_export_size(dialog.pixel_size()) if dialog.has_size_set() else nullcontext():
                # 这里每次截图都重新构建一下，因为如果复用原来的对象会使得和 GUI 的上下文冲突
                built = self.built.timeline.__class__().build()
                built.capture(t, transparent=transparent).save(file_path)

        except Exception as e:
            if not isinstance(e, ExitException):
                traceback.print_exc()
        else:
            ret = True

        if ret:
            log.info(_('Frame t={t:.2f} saved to "{file_path}"').format(t=t, file_path=file_path))
            QMessageBox.information(self,
                                    _('Note'),
                                    _('Captured to {file_path}').format(file_path=file_path))
            if dialog.open():
                open_file(file_path)

    def on_export_clicked(self) -> None:
        self.play_timer.stop()

        dialog = ExportDialog(self.built, self.timeline_view.inout_point is not None, self)
        ret = dialog.exec()
        if not ret:
            return

        file_path = dialog.file_path()
        cli_config.fps = dialog.fps()
        using_inout_point = dialog.using_inout_point()
        hwaccel = dialog.hwaccel()
        video_with_audio = (self.built.timeline.has_audio_for_all() and not file_path.endswith('gif'))

        QMessageBox.information(self,
                                _('Note'),
                                _('Output will start shortly. Please check the console for information.'))
        self.hide()
        QApplication.processEvents()
        ret = False
        try:
            with self.change_export_size(dialog.pixel_size()) if dialog.has_size_set() else nullcontext():
                built = self.built.timeline.__class__().build()

                args = [file_path]
                if using_inout_point:
                    args += self.timeline_view.inout_point

                if video_with_audio:
                    video_writer = VideoWriter(built)
                    video_writer.write_all(*args, hwaccel=hwaccel, _keep_temp=True)

                    audio_file_path = os.path.splitext(file_path)[0] + '.mp3'

                    audio_writer = AudioWriter(built)
                    audio_writer.write_all(audio_file_path, _keep_temp=True)

                    merge_video_and_audio(built.cfg.ffmpeg_bin,
                                          video_writer.temp_file_path,
                                          audio_writer.temp_file_path,
                                          video_writer.final_file_path)
                else:
                    video_writer = VideoWriter(built)
                    video_writer.write_all(*args, hwaccel=hwaccel)

        except Exception as e:
            if not isinstance(e, ExitException):
                traceback.print_exc()
        except KeyboardInterrupt:
            log.warning(_('Exporting was cancelled'))
        else:
            ret = True

        self.show()
        if ret:
            QMessageBox.information(self,
                                    _('Note'),
                                    _('Output to {file_path} has been completed.').format(file_path=file_path))
            if dialog.open():
                open_file(file_path)

    @contextmanager
    def change_export_size(self, size: tuple[int, int]):
        old_size = cli_config.pixel_width, cli_config.pixel_height
        cli_config.pixel_width, cli_config.pixel_height = size
        try:
            yield
        finally:
            cli_config.pixel_width, cli_config.pixel_height = old_size

    # endregion (slots-anim)

    # endregion (slots)

    # region network

    def setup_socket(self, client_search_port: int) -> None:
        from PySide6.QtNetwork import QHostAddress, QUdpSocket

        ret = False
        self.shared_socket = QUdpSocket()
        if 1024 <= client_search_port <= 65535:
            ret = self.shared_socket.bind(QHostAddress.SpecialAddress.LocalHost,
                                          client_search_port,
                                          QUdpSocket.BindFlag.ShareAddress | QUdpSocket.BindFlag.ReuseAddressHint)
            if ret:
                self.shared_socket.readyRead.connect(self.on_shared_ready_read)
                log.info(
                    _('Searching port has been opened at {port}')
                    .format(port=client_search_port)
                )
            else:
                log.warning(
                    _('Failed to open searching port at {port}')
                    .format(port=client_search_port)
                )
        else:
            log.warning(
                _('Searching port {port} is invalid, '
                  'please use a number between 1024 and 65535 instead')
                .format(port=client_search_port)
            )

        if not ret:
            log.warning(_('Interactive development is disabled '
                          'because the searching port is not established.'))
            self.socket = None
            return

        self.socket = QUdpSocket()
        self.socket.bind()

        self.socket.readyRead.connect(self.on_ready_read)

        self.clients: set[tuple[QHostAddress, int]] = set()
        self.lineno = -1

        log.info(_('Interactive port has been opened at {port}').format(port=self.socket.localPort()))
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
                                file_path=os.path.abspath(inspect.getfile(self.built.timeline.__class__))
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
                        self.clients.add((datagram.senderAddress(), datagram.senderPort()))
                        self.send_lineno(self.lineno)

                    # 重新构建
                    case 'file_saved':
                        if os.path.samefile(janim['file_path'], inspect.getmodule(self.built.timeline).__file__):
                            self.on_rebuild_triggered()

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

    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)

        if self.socket is not None:
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

        self.save_options()

    if sys.platform == "darwin":
        def eventFilter(self, watched, event):
            if self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint:
                if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.NonClientAreaMouseButtonPress):
                    for obj in self.children():
                        if getattr(obj, ACTION_WIDGET_FLAG_KEY, False):
                            obj.raise_()
            return super().eventFilter(watched, event)

    # endregion
