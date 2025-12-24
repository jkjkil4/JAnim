from __future__ import annotations

import os
import traceback
from contextlib import contextmanager, nullcontext
from typing import TYPE_CHECKING

from PySide6.QtCore import SignalInstance
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox

from janim.exception import ExitException
from janim.gui.output.capture_dialog import CaptureDialog
from janim.gui.output.export_dialog import ExportDialog
from janim.locale.i18n import get_translator
from janim.logger import log
from janim.render.writer import AudioWriter, VideoWriter, merge_video_and_audio
from janim.utils.config import cli_config
from janim.utils.file_ops import open_file

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.output.__init__')


def setup_output_actions(viewer: AnimViewer, menu: QMenu) -> None:
    action_export = menu.addAction(_('Export(&E)'))
    action_export.setShortcut('Ctrl+S')
    action_export.setAutoRepeat(False)

    action_capture = menu.addAction(_('Capture(&C)'))
    action_capture.setShortcut('Ctrl+Alt+S')
    action_capture.setAutoRepeat(False)

    connect_to_output_slots(viewer, action_capture.triggered, action_export.triggered)


def connect_to_output_slots(viewer: AnimViewer, capture_signal: SignalInstance, export_signal: SignalInstance) -> None:
    capture_signal.connect(lambda: on_capture_clicked(viewer))
    export_signal.connect(lambda: on_export_clicked(viewer))


def on_capture_clicked(self: AnimViewer) -> None:
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
        with change_export_size(dialog.pixel_size()) if dialog.has_size_set() else nullcontext():
            # 这里每次截图都重新构建一下，因为如果复用原来的对象会使得和 GUI 的上下文冲突
            built = self.built.timeline.__class__().build()
            built.capture(t, transparent=transparent, ctx=self.glw.ctx).save(file_path)

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


def on_export_clicked(self: AnimViewer) -> None:
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
        with change_export_size(dialog.pixel_size()) if dialog.has_size_set() else nullcontext():
            built = self.built.timeline.__class__().build()

            args = [file_path]
            if using_inout_point:
                args += self.timeline_view.inout_point

            if video_with_audio:
                video_writer = VideoWriter(built, ctx=self.glw.ctx)
                video_writer.write_all(*args, hwaccel=hwaccel, _keep_temp=True)

                audio_file_path = os.path.splitext(file_path)[0] + '.mp3'

                audio_writer = AudioWriter(built)
                audio_writer.write_all(audio_file_path, _keep_temp=True)

                merge_video_and_audio(built.cfg.ffmpeg_bin,
                                      video_writer.temp_file_path,
                                      audio_writer.temp_file_path,
                                      video_writer.final_file_path)
            else:
                video_writer = VideoWriter(built, ctx=self.glw.ctx)
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
def change_export_size(size: tuple[int, int]):
    old_size = cli_config.pixel_width, cli_config.pixel_height
    cli_config.pixel_width, cli_config.pixel_height = size
    try:
        yield
    finally:
        cli_config.pixel_width, cli_config.pixel_height = old_size
