import math
import os
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog,
                               QMessageBox, QWidget)

from janim.anims.timeline import BuiltTimeline
from janim.gui.functions.ui_ExportDialog import Ui_ExportDialog
from janim.locale.i18n import get_local_strings
from janim.utils.config import Config
from janim.utils.file_ops import getfile_or_empty

_ = get_local_strings('export_dialog')


class ExportDialog(QDialog):
    def __init__(self, built: BuiltTimeline, parent: QWidget | None = None):
        super().__init__(parent)
        self.built = built
        self.code_file_path = getfile_or_empty(self.built.timeline.__class__)

        self.setup_ui()
        self.setup_contents()
        self.setup_slots()

    def setup_ui(self) -> None:
        self.ui = Ui_ExportDialog()
        self.ui.setupUi(self)

        self.setWindowTitle(_('Export'))
        self.ui.label_path.setText(_('Export Path:'))
        self.ui.label_fps.setText(_('FPS:'))
        self.ui.label_size.setText(_('Size:'))
        self.ui.ckb_hwaccel.setText(_('Hardware Acceleration'))
        self.ui.ckb_open.setText(_('Open the video after exporting'))

        btn_ok = self.ui.btn_box.button(QDialogButtonBox.StandardButton.Ok)
        btn_ok.setText(_('OK'))

        btn_cancel = self.ui.btn_box.button(QDialogButtonBox.StandardButton.Cancel)
        btn_cancel.setText(_('Cancel'))

    def setup_contents(self) -> None:
        w, h = self.built.cfg.pixel_width, self.built.cfg.pixel_height
        for factor, desc in [
            (2, '200%'),         # 4K
            (4 / 3, '133.33%'),  # 1440p
            (1, '100%'),         # 1080p
            (2 / 3, '66.67%'),   # 720p
            (4 / 9, '44.44%'),   # 480p
            (1 / 3, '33.33%'),   # 360p
        ]:
            scaled_w = math.ceil(w * factor)
            scaled_h = math.ceil(h * factor)
            self.ui.cbb_size.addItem(f'{scaled_w}x{scaled_h} ({desc})', (factor, scaled_w, scaled_h))
            self.ui.cbb_size.setCurrentIndex(2)

        self.load_options()

    def setup_slots(self) -> None:
        self.ui.btn_browse.clicked.connect(self.on_btn_browse_clicked)
        self.ui.btn_box.accepted.connect(self.on_accepted)

    def load_options(self) -> None:
        settings = QSettings(os.path.join(Config.get.temp_dir, 'export_dialog.ini'), QSettings.Format.IniFormat)
        settings.beginGroup(self.code_file_path)
        output_dir = settings.value('output_dir', None)
        fps = settings.value('fps', self.built.cfg.fps, type=int)
        scale = settings.value('scale', 1.0, type=float)
        hwaccel = settings.value('hwaccel', False, type=bool)
        open_after_export = settings.value('open', False, type=bool)
        settings.endGroup()

        if output_dir is None:
            relative_path = os.path.dirname(self.code_file_path)
            output_dir = self.built.cfg.formated_output_dir(relative_path)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        file_path = os.path.join(output_dir, f'{self.built.timeline.__class__.__name__}.mp4')

        self.ui.edit_path.setText(file_path)
        self.ui.spb_fps.setValue(fps)
        for i in range(self.ui.cbb_size.count()):
            factor, _, _ = self.ui.cbb_size.itemData(i)
            if factor == scale:
                self.ui.cbb_size.setCurrentIndex(i)
                break
        self.ui.ckb_hwaccel.setChecked(hwaccel)
        self.ui.ckb_open.setChecked(open_after_export)

    def save_options(self) -> None:
        settings = QSettings(os.path.join(Config.get.temp_dir, 'export_dialog.ini'), QSettings.Format.IniFormat)
        settings.beginGroup(self.code_file_path)
        settings.setValue('output_dir', os.path.dirname(self.ui.edit_path.text()))
        settings.setValue('fps', self.ui.spb_fps.value())
        settings.setValue('scale', self.ui.cbb_size.currentData()[0])
        settings.setValue('hwaccel', self.ui.ckb_hwaccel.isChecked())
        settings.setValue('open', self.ui.ckb_open.isChecked())
        settings.endGroup()

    def file_path(self) -> str:
        return self.ui.edit_path.text()

    def fps(self) -> int:
        return self.ui.spb_fps.value()

    def has_size_set(self) -> bool:
        factor, _, _ = self.ui.cbb_size.currentData()
        return factor != 1

    def size(self) -> tuple[int, int]:
        _, w, h = self.ui.cbb_size.currentData()
        return w, h

    def hwaccel(self) -> bool:
        return self.ui.ckb_hwaccel.isChecked()

    def open(self) -> bool:
        return self.ui.ckb_open.isChecked()

    def on_btn_browse_clicked(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            '',
            self.ui.edit_path.text(),
            'MP4 (*.mp4);;MOV (*.mov);;GIF (*.gif)',
            '',
            QFileDialog.Option.DontConfirmOverwrite
        )
        if not file_path:
            return

        path = Path(file_path).resolve()
        cwd = Path.cwd()
        try:
            path = path.relative_to(cwd)
        except ValueError:
            pass

        self.ui.edit_path.setText(str(path))

    def on_accepted(self) -> None:
        file_path = self.file_path()
        if os.path.exists(file_path):
            msgbox = QMessageBox(
                QMessageBox.Icon.Warning,
                _('Confirm Export'),
                _('{filename} already exists.\nDo you want to replace it?')
                .format(filename=os.path.basename(file_path)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                self
            )
            msgbox.setDefaultButton(QMessageBox.StandardButton.Yes)
            msgbox.setButtonText(QMessageBox.StandardButton.Yes, _('Yes(&Y)'))
            msgbox.setButtonText(QMessageBox.StandardButton.No, _('No(&N)'))
            ret = msgbox.exec()
            if ret == QMessageBox.StandardButton.No:
                return

        self.save_options()
        self.accept()
