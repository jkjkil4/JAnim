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
import time
import traceback
from bisect import bisect_left
from typing import Sequence

from PySide6.QtCore import QByteArray, Qt, Signal
from PySide6.QtGui import QCloseEvent, QHideEvent, QIcon, QShowEvent
from PySide6.QtWidgets import (QApplication, QCompleter, QLabel, QLineEdit,
                               QMainWindow, QMessageBox, QPushButton,
                               QSizePolicy, QSplitter, QStackedLayout, QWidget)

from janim.anims.timeline import Timeline, TimelineAnim
from janim.exception import ExitException
from janim.gui.application import Application
from janim.gui.audio_player import AudioPlayer
from janim.gui.color_widget import ColorWidget
from janim.gui.export_dialog import ExportDialog
from janim.gui.fixed_ratio_widget import FixedRatioWidget
from janim.gui.font_table import FontTable
from janim.gui.glwidget import GLWidget
from janim.gui.painter import Painter
from janim.gui.precise_timer import PreciseTimer
from janim.gui.richtext_editor import RichTextEditor
from janim.gui.selector import Selector
from janim.gui.timeline_view import TimelineView
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.writer import AudioWriter, VideoWriter, merge_video_and_audio
from janim.utils.config import cli_config
from janim.utils.file_ops import get_janim_dir, open_file

_ = get_local_strings('anim_viewer')


class AnimViewer(QMainWindow):
    '''
    用于显示构建完成的时间轴动画

    可以使用 ``AnimViewer.views(MyTimeline().build())`` 进行直接显示
    '''
    play_finished = Signal()

    def __init__(
        self,
        anim: TimelineAnim,
        *,
        auto_play: bool = True,
        interact: bool = False,
        available_timeline_names: Sequence[str] | None = None,
        parent: QWidget | None = None
    ):
        super().__init__(parent)

        self.setup_ui()
        self.setup_play_timer()
        if interact:
            self.setup_socket(anim.cfg.client_search_port)
        else:
            self.socket = None
        self.audio_player = None

        self.setup_slots()

        self.set_anim(anim)

        self.timeline_view.value_changed.emit(0)
        self.action_stay_on_top.setChecked(True)

        if auto_play:
            self.switch_play_state()

        if available_timeline_names is not None:
            self.update_completer(available_timeline_names)

    @classmethod
    def views(cls, anim: TimelineAnim, **kwargs) -> None:
        '''
        直接显示一个浏览构建完成的时间轴动画的窗口
        '''
        app = Application.instance()
        if app is None:
            app = Application()

        w = cls(anim, **kwargs)
        w.show()

        app.exec()

    def set_anim(self, anim: TimelineAnim) -> None:
        self.anim = anim

        # data
        def to_progress(p: Timeline.PausePoint) -> int:
            rough_progress = p.at * self.anim.cfg.preview_fps

            if rough_progress % 1 < 1e-3:
                result = int(rough_progress)
            else:
                result = int(rough_progress) + 1

            if p.at_previous_frame:
                result -= 1

            return result

        self.pause_progresses = list(map(to_progress, anim.timeline.pause_points))
        self.pause_progresses.sort()

        # menu bar
        if self.selector is not None:
            self.selector.deleteLater()

        # central widget
        self.fixed_ratio_widget.set_src_size((anim.cfg.pixel_width, anim.cfg.pixel_height))
        self.glw.set_anim(anim)
        self.timeline_view.set_anim(anim, self.pause_progresses)

        # status bar
        self.name_edit.setText(anim.timeline.__class__.__name__)

        # other
        self.play_timer.set_duration(1 / anim.cfg.preview_fps)

        if self.anim.timeline.has_audio() and self.audio_player is None:
            self.audio_player = AudioPlayer(self.anim.cfg.audio_framerate, self.anim.cfg.audio_channels)

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
        self.timeline_view.setFocus()

    def setup_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        menu_functions = menu_bar.addMenu(_('Functions(&F)'))

        self.action_stay_on_top = menu_functions.addAction(_('Stay on top(&T)'))
        self.action_stay_on_top.setCheckable(True)
        self.action_stay_on_top.setShortcut('Ctrl+T')

        menu_functions.addSeparator()

        self.action_rebuild = menu_functions.addAction(_('Rebuild(&L)'))
        self.action_rebuild.setShortcut('Ctrl+L')

        menu_functions.addSeparator()

        self.action_select = menu_functions.addAction(_('Subitem selector(&S)'))
        self.action_select.setShortcut('Ctrl+S')
        self.selector: Selector | None = None

        self.action_painter = menu_functions.addAction(_('Draw(&D)'))
        self.action_painter.setShortcut('Ctrl+D')
        self.painter: Painter | None = None

        self.action_richtext_edit = menu_functions.addAction(_('Rich text editor(&R)'))
        self.action_richtext_edit.setShortcut('Ctrl+R')
        self.richtext_editor: RichTextEditor | None = None

        self.action_font_table = menu_functions.addAction(_('Font list(&F)'))
        self.action_font_table.setShortcut('Ctrl+F')
        self.font_table: FontTable | None = None

        self.action_color_widget = menu_functions.addAction(_('Color(&O)'))
        self.action_color_widget.setShortcut('Ctrl+O')
        self.color_widget: ColorWidget | None = None

    def setup_status_bar(self) -> None:
        self.fps_label = QLabel()
        self.time_label = QLabel()
        self.name_edit = QLineEdit()
        self.btn_export = QPushButton()
        self.btn_export.setIcon(QIcon(os.path.join(get_janim_dir(), 'gui', 'export.png')))
        self.btn_export.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        stb = self.statusBar()
        stb.setFixedHeight(stb.height())
        stb.setContentsMargins(0, 0, 0, 0)
        stb.addWidget(self.fps_label)
        stb.addPermanentWidget(self.name_edit)
        stb.addPermanentWidget(self.time_label)
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
        window_position = self.anim.cfg.wnd_pos
        window_monitor = self.anim.cfg.wnd_monitor

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

        self.setGeometry(geometry)

    def update_completer(self, completions: Sequence[str]) -> None:
        completer = QCompleter(completions)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_edit.setCompleter(completer)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self.moved_to_position:
            self.move_to_position()
            self.moved_to_position = True

    # endregion (setup_ui)

    # region play_timer

    def setup_play_timer(self) -> None:
        self.play_timer = PreciseTimer(parent=self)

        self.fps_counter = 0
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
        self.action_stay_on_top.toggled.connect(self.on_stay_on_top_toggled)
        self.action_rebuild.triggered.connect(self.on_rebuild_triggered)
        self.action_select.triggered.connect(self.on_select_triggered)
        self.action_painter.triggered.connect(self.on_painter_triggered)
        self.action_richtext_edit.triggered.connect(self.on_richtext_edit_triggered)
        self.action_font_table.triggered.connect(self.on_font_table_triggered)
        self.action_color_widget.triggered.connect(self.on_color_widget_triggered)

        self.timeline_view.value_changed.connect(self.on_value_changed)
        self.timeline_view.dragged.connect(lambda: self.set_play_state(False))
        self.timeline_view.space_pressed.connect(lambda: self.switch_play_state())

        self.play_timer.timeout.connect(self.on_play_timer_timeout)
        self.glw.rendered.connect(self.on_glw_rendered)
        self.name_edit.editingFinished.connect(self.on_name_edit_finished)
        self.btn_export.clicked.connect(self.on_export_clicked)

    # region slots-menu

    def on_stay_on_top_toggled(self, flag: bool) -> None:
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, flag)
        if visible:
            self.setVisible(True)

    def on_rebuild_triggered(self) -> None:
        module = inspect.getmodule(self.anim.timeline)
        progress = self.timeline_view.progress()
        preview_fps = self.anim.cfg.preview_fps

        name = self.name_edit.text().strip()
        stay_same = self.anim.timeline.__class__.__name__ == name

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
            anim: TimelineAnim = timeline_class().build()
        except Exception as e:
            if not isinstance(e, ExitException):
                traceback.print_exc()
            log.error(_('Failed to rebuild'))
            return

        range = self.timeline_view.range
        self.set_anim(anim)

        import gc

        from janim.cli import get_all_timelines_from_module

        gc.collect()
        get_all_timelines_from_module.cache_clear()
        self.update_completer([timeline.__name__ for timeline in get_all_timelines_from_module(module)])

        if not stay_same:
            self.anim.anim_on(0)
            self.timeline_view.set_progress(0)
        else:
            # 把原来进度（所在第几帧）转换到新的进度
            # 如果帧率没变，则进度不变
            # 如果帧率变了，例如从 30fps 到 60fps，则进度 43 对应 进度 86（乘了 2）
            self.play_timer.duration = 1 / self.anim.cfg.preview_fps
            progress = int(progress * self.anim.cfg.preview_fps / preview_fps)
            self.anim.anim_on(self.timeline_view.progress_to_time(progress))
            self.timeline_view.set_progress(progress)

            # 设置 range 是为了保留动画标签的相对位置
            # 比如，本来是 0~1s 和 1~2s 分别一个动画
            # 重新构建后，只剩下了 0~1s 的动画
            # 那么仍保留原来的显示范围，使得 0~1s 的显示位置不变，虽然显示范围超出了持续时间
            self.timeline_view.range = range

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
            self.send_lineno(self.anim.timeline.get_lineno_at_time(time))

    def on_select_triggered(self) -> None:
        if self.selector is None:
            self.selector = Selector(self)
            self.selector.destroyed.connect(self.on_selector_destroyed)
        else:
            self.selector.clear()

    def on_selector_destroyed(self) -> None:
        self.selector = None

    def on_painter_triggered(self) -> None:
        if self.painter is None:
            self.painter = Painter(self)
            self.painter.setWindowFlag(Qt.WindowType.Tool)
            self.painter.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.painter.destroyed.connect(self.on_painter_destroyed)
        self.painter.show()

    def on_painter_destroyed(self) -> None:
        self.painter = None

    def on_richtext_edit_triggered(self) -> None:
        if self.richtext_editor is None:
            self.richtext_editor = RichTextEditor(self)
            self.richtext_editor.setWindowFlag(Qt.WindowType.Tool)
            self.richtext_editor.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.richtext_editor.destroyed.connect(self.on_richtext_editor_destroyed)
        self.richtext_editor.show()

    def on_richtext_editor_destroyed(self) -> None:
        self.richtext_editor = None

    def on_font_table_triggered(self) -> None:
        if self.font_table is None:
            self.font_table = FontTable(self)
            self.font_table.setWindowFlag(Qt.WindowType.Tool)
            self.font_table.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.font_table.destroyed.connect(self.on_font_table_destroyed)
        self.font_table.show()

    def on_font_table_destroyed(self) -> None:
        self.font_table = None

    def on_color_widget_triggered(self) -> None:
        if self.color_widget is None:
            self.color_widget = ColorWidget(self)
            self.color_widget.setWindowFlag(Qt.WindowType.Tool)
            self.color_widget.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.color_widget.destroyed.connect(self.on_color_widget_destroyed)
        self.color_widget.show()

    def on_color_widget_destroyed(self) -> None:
        self.color_widget = None

    # endregion (slots-menu)

    # region slots-anim

    def on_value_changed(self, value: int) -> None:
        time = self.timeline_view.progress_to_time(value)

        if self.socket is not None:
            line = self.anim.timeline.get_lineno_at_time(time)

            if line != self.lineno:
                self.lineno = line

                self.send_lineno(line)

        self.glw.set_time(time)
        self.time_label.setText(f'{time:.1f}/{self.anim.global_range.duration:.1f} s')

    def on_glw_rendered(self) -> None:
        cur = time.time()
        self.fps_counter += 1
        if cur - self.fps_record_start >= 1:
            # i18n?
            self.fps_label.setText(f'Preview FPS: {self.fps_counter}/{self.anim.cfg.preview_fps}')
            self.fps_counter = 0
            self.fps_record_start = cur

    def on_play_timer_timeout(self) -> None:
        if self.anim.timeline.has_audio():
            samples = self.anim.timeline.get_audio_samples_of_frame(self.anim.cfg.preview_fps,
                                                                    self.anim.cfg.audio_framerate,
                                                                    self.timeline_view.progress())
            self.audio_player.write(samples.tobytes())

        self.timeline_view.set_progress(self.timeline_view.progress() + 1)

        if self.pause_progresses:
            progress = self.timeline_view.progress()
            idx = bisect_left(self.pause_progresses, progress)
            if idx < len(self.pause_progresses) and self.pause_progresses[idx] == progress:
                self.play_timer.stop()

        if self.timeline_view.at_end():
            self.play_finished.emit()
            self.play_timer.stop()

    def on_name_edit_finished(self) -> None:
        if self.name_edit.text().strip() != self.anim.timeline.__class__.__name__:
            self.play_timer.stop()
            self.on_rebuild_triggered()
            self.timeline_view.setFocus()

    def on_export_clicked(self) -> None:
        self.play_timer.stop()

        dialog = ExportDialog(self.anim, self)
        ret = dialog.exec()
        if not ret:
            return

        cli_config.fps = dialog.fps()
        file_path = dialog.file_path()
        video_with_audio = (self.anim.timeline.has_audio() and not file_path.endswith('gif'))

        QMessageBox.information(self,
                                _('Note'),
                                _('Output will start shortly. Please check the console for information.'))
        self.hide()
        QApplication.processEvents()
        ret = False
        try:
            anim = self.anim.timeline.__class__().build()

            if video_with_audio:
                video_writer = VideoWriter(anim)
                video_writer.write_all(file_path, _keep_temp=True)

                audio_file_path = os.path.splitext(file_path)[0] + '.mp3'

                audio_writer = AudioWriter(anim)
                audio_writer.write_all(audio_file_path, _keep_temp=True)

                merge_video_and_audio(anim.cfg.ffmpeg_bin,
                                      video_writer.temp_file_path,
                                      audio_writer.temp_file_path,
                                      video_writer.final_file_path)
            else:
                video_writer = VideoWriter(anim)
                video_writer.write_all(file_path)

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

    # endregion (slots-anim)

    # endregion (slots)

    # region network

    def setup_socket(self, client_search_port: int) -> None:
        from PySide6.QtNetwork import QHostAddress, QUdpSocket

        ret = False
        self.shared_socket = QUdpSocket()
        if 1024 <= client_search_port <= 65535:
            ret = self.shared_socket.bind(client_search_port,
                                          QUdpSocket.BindFlag.ShareAddress | QUdpSocket.BindFlag.ReuseAddressHint)
            if ret:
                self.shared_socket.readyRead.connect(self.on_shared_ready_read)
                log.debug(
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

        self.clients: list[tuple[QHostAddress, int]] = []
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

    # endregion
