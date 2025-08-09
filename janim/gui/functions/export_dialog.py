import inspect
import math
import os
from pathlib import Path

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog,
                               QMessageBox, QWidget)

from janim.anims.timeline import BuiltTimeline
from janim.gui.functions.ui_ExportDialog import Ui_ExportDialog
from janim.locale.i18n import get_local_strings

_ = get_local_strings('export_dialog')


class ExportDialog(QDialog):
    def __init__(self, built: BuiltTimeline, parent: QWidget | None = None):
        super().__init__(parent)
        self.built = built

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
        relative_path = os.path.dirname(inspect.getfile(self.built.timeline.__class__))
        output_dir = self.built.cfg.formated_output_dir(relative_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        file_path = os.path.join(output_dir, f'{self.built.timeline.__class__.__name__}.mp4')

        self.ui.edit_path.setText(file_path)
        self.ui.spb_fps.setValue(self.built.cfg.fps)

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

    def setup_slots(self) -> None:
        self.ui.btn_browse.clicked.connect(self.on_btn_browse_clicked)
        self.ui.btn_box.accepted.connect(self.on_accepted)

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

        self.accept()
