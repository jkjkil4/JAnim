import math
import os
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog,
                               QMessageBox, QWidget)

from janim.anims.timeline import BuiltTimeline
from janim.gui.functions.ui_ExportDialog import QComboBox, Ui_ExportDialog
from janim.locale.i18n import get_local_strings
from janim.utils.config import Config
from janim.utils.file_ops import getfile_or_empty

_ = get_local_strings('export_dialog')


class ExportDialog(QDialog):
    def __init__(self, built: BuiltTimeline, is_inout_point_set: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self.built = built
        self.is_inout_point_set = is_inout_point_set
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

        self.ui.label_range.setText(_('Range:'))
        self.ui.rbtn_full.setText(_('Full'))
        if self.is_inout_point_set:
            self.ui.rbtn_inout.setText(_('In/Out Point'))
        else:
            self.ui.rbtn_inout.setText(_('In/Out Point (Not Set)'))
            self.ui.rbtn_inout.setEnabled(False)

        self.ui.ckb_hwaccel.setText(_('Hardware Acceleration'))
        self.ui.ckb_open.setText(_('Open the video after exporting'))

        btn_ok = self.ui.btn_box.button(QDialogButtonBox.StandardButton.Ok)
        btn_ok.setText(_('OK'))

        btn_cancel = self.ui.btn_box.button(QDialogButtonBox.StandardButton.Cancel)
        btn_cancel.setText(_('Cancel'))

    @staticmethod
    def setup_size_combobox(cbb_size: QComboBox, w: int, h: int) -> None:
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
            cbb_size.addItem(f'{scaled_w}x{scaled_h} ({desc})', (factor, scaled_w, scaled_h))
            cbb_size.setCurrentIndex(2)

    def setup_contents(self) -> None:
        w, h = self.built.cfg.pixel_width, self.built.cfg.pixel_height
        self.setup_size_combobox(self.ui.cbb_size, w, h)

        self.load_options()

    def setup_slots(self) -> None:
        self.ui.btn_browse.clicked.connect(self.on_btn_browse_clicked)
        self.ui.btn_box.accepted.connect(self.on_accepted)

    @staticmethod
    def load_size_combobox(cbb_size: QComboBox, scale: float) -> None:
        for i in range(cbb_size.count()):
            factor, _, _ = cbb_size.itemData(i)
            if factor == scale:
                cbb_size.setCurrentIndex(i)
                break

    def load_options(self) -> None:
        settings = QSettings(os.path.join(Config.get.temp_dir, 'export_dialog.ini'), QSettings.Format.IniFormat)
        settings.beginGroup(self.code_file_path)
        output_dir = settings.value('output_dir', None)
        output_format = settings.value('output_format', '.mp4')
        fps = settings.value('fps', self.built.cfg.fps, type=int)
        scale = settings.value('scale', 1.0, type=float)
        using_inout_point = settings.value('using_inout_point', False, type=bool)
        hwaccel = settings.value('hwaccel', False, type=bool)
        open_after_export = settings.value('open', False, type=bool)
        settings.endGroup()

        if output_dir is None:
            relative_path = os.path.dirname(self.code_file_path)
            output_dir = self.built.cfg.formated_output_dir(relative_path)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        file_path = os.path.join(output_dir, f'{self.built.timeline.__class__.__name__}{output_format}')

        self.ui.edit_path.setText(file_path)
        self.ui.spb_fps.setValue(fps)
        self.load_size_combobox(self.ui.cbb_size, scale)

        if using_inout_point and self.ui.rbtn_inout.isEnabled():
            self.ui.rbtn_inout.setChecked(True)

        self.ui.ckb_hwaccel.setEnabled(output_format == '.mp4')
        self.ui.ckb_hwaccel.setChecked(hwaccel)
        self.ui.ckb_open.setChecked(open_after_export)

    def save_options(self) -> None:
        path = Path(self.ui.edit_path.text())

        settings = QSettings(os.path.join(Config.get.temp_dir, 'export_dialog.ini'), QSettings.Format.IniFormat)
        settings.beginGroup(self.code_file_path)
        settings.setValue('output_dir', path.parent)
        settings.setValue('output_format', path.suffix)
        settings.setValue('fps', self.ui.spb_fps.value())
        settings.setValue('scale', self.ui.cbb_size.currentData()[0])
        settings.setValue('using_inout_point', self.ui.rbtn_inout.isChecked())
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

    def pixel_size(self) -> tuple[int, int]:
        _, w, h = self.ui.cbb_size.currentData()
        return w, h

    def using_inout_point(self) -> bool:
        return self.ui.rbtn_inout.isChecked()

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
            suffix_to_filter_map[Path(self.ui.edit_path.text()).suffix],
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
        self.ui.ckb_hwaccel.setEnabled(path.suffix == '.mp4')

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


suffix_to_filter_map = {
    '.mp4': 'MP4 (*.mp4)',
    '.mov': 'MOV (*.mov)',
    '.gif': 'GIF (*.gif)',
}
