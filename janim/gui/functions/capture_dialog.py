import os
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog,
                               QMessageBox, QWidget)

from janim.anims.timeline import BuiltTimeline
from janim.gui.functions.export_dialog import ExportDialog
from janim.gui.functions.ui_CaptureDialog import Ui_CaptureDialog
from janim.locale.i18n import get_local_strings
from janim.utils.config import Config
from janim.utils.file_ops import getfile_or_empty

_ = get_local_strings('capture_dialog')


class CaptureDialog(QDialog):
    def __init__(self, built: BuiltTimeline, parent: QWidget | None = None):
        super().__init__(parent)
        self.built = built
        self.code_file_path = getfile_or_empty(self.built.timeline.__class__)

        self.setup_ui()
        self.setup_contents()
        self.setup_slots()

    def setup_ui(self) -> None:
        self.ui = Ui_CaptureDialog()
        self.ui.setupUi(self)

        self.setWindowTitle(_('Capture'))
        self.ui.label_path.setText(_('Save Path:'))
        self.ui.label_size.setText(_('Size:'))
        self.ui.ckb_transparent.setText(_('Transparent Background'))
        self.ui.ckb_open.setText(_('Open the image after capturing'))

        btn_ok = self.ui.btn_box.button(QDialogButtonBox.StandardButton.Ok)
        btn_ok.setText(_('OK'))

        btn_cancel = self.ui.btn_box.button(QDialogButtonBox.StandardButton.Cancel)
        btn_cancel.setText(_('Cancel'))

    def setup_contents(self) -> None:
        w, h = self.built.cfg.pixel_width, self.built.cfg.pixel_height
        ExportDialog.setup_size_combobox(self.ui.cbb_size, w, h)

        self.load_options()

    def setup_slots(self) -> None:
        self.ui.btn_browse.clicked.connect(self.on_btn_browse_clicked)
        self.ui.btn_box.accepted.connect(self.on_accepted)

    def load_options(self) -> None:
        settings = QSettings(os.path.join(Config.get.temp_dir, 'capture_dialog.ini'), QSettings.Format.IniFormat)
        settings.beginGroup(self.code_file_path)
        output_dir = settings.value('output_dir', None)
        scale = settings.value('scale', 1.0, type=float)
        transparent = settings.value('transparent', True, type=bool)
        open_after_capture = settings.value('open', False, type=bool)
        settings.endGroup()

        if output_dir is None:
            relative_path = os.path.dirname(self.code_file_path)
            output_dir = self.built.cfg.formated_output_dir(relative_path)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        file_path = os.path.join(output_dir, f'{self.built.timeline.__class__.__name__}.png')
        self.ui.edit_path.setText(file_path)
        ExportDialog.load_size_combobox(self.ui.cbb_size, scale)
        self.ui.ckb_transparent.setChecked(transparent)
        self.ui.ckb_open.setChecked(open_after_capture)

    def save_options(self) -> None:
        settings = QSettings(os.path.join(Config.get.temp_dir, 'capture_dialog.ini'), QSettings.Format.IniFormat)
        settings.beginGroup(self.code_file_path)
        settings.setValue('output_dir', os.path.dirname(self.file_path()))
        settings.setValue('scale', self.ui.cbb_size.currentData()[0])
        settings.setValue('transparent', self.transparent())
        settings.setValue('open', self.open())
        settings.endGroup()

    def file_path(self) -> str:
        return self.ui.edit_path.text()

    def has_size_set(self) -> bool:
        factor, _, _ = self.ui.cbb_size.currentData()
        return factor != 1

    def pixel_size(self) -> tuple[int, int]:
        _, w, h = self.ui.cbb_size.currentData()
        return w, h

    def transparent(self) -> bool:
        return self.ui.ckb_transparent.isChecked()

    def open(self) -> bool:
        return self.ui.ckb_open.isChecked()

    def on_btn_browse_clicked(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            '',
            self.ui.edit_path.text(),
            'PNG (*.png)',
            '',
            QFileDialog.Option.DontConfirmOverwrite
        )
        if not file_path:
            return

        path = Path(file_path)
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
