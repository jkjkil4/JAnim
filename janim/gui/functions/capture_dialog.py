import inspect
import os
from pathlib import Path

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog,
                               QMessageBox, QWidget)

from janim.anims.timeline import BuiltTimeline
from janim.gui.functions.ui_CaptureDialog import Ui_CaptureDialog
from janim.locale.i18n import get_local_strings

_ = get_local_strings('capture_dialog')


class CaptureDialog(QDialog):
    def __init__(self, built: BuiltTimeline, parent: QWidget | None = None):
        super().__init__(parent)
        self.built = built

        self.setup_ui()
        self.setup_contents()
        self.setup_slots()

    def setup_ui(self) -> None:
        self.ui = Ui_CaptureDialog()
        self.ui.setupUi(self)

        self.setWindowTitle(_('Capture'))
        self.ui.label_path.setText(_('Save Path:'))
        self.ui.ckb_transparent.setText(_('Transparent Background'))
        self.ui.ckb_open.setText(_('Open the image after capturing'))

        btn_ok = self.ui.btn_box.button(QDialogButtonBox.StandardButton.Ok)
        btn_ok.setText(_('OK'))

        btn_cancel = self.ui.btn_box.button(QDialogButtonBox.StandardButton.Cancel)
        btn_cancel.setText(_('Cancel'))

    def setup_contents(self) -> None:
        relative_path = os.path.dirname(inspect.getfile(self.built.timeline.__class__))
        output_dir = self.built.cfg.formated_output_dir(relative_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        file_path = os.path.join(output_dir, f'{self.built.timeline.__class__.__name__}.png')

        self.ui.edit_path.setText(file_path)

    def setup_slots(self) -> None:
        self.ui.btn_browse.clicked.connect(self.on_btn_browse_clicked)
        self.ui.btn_box.accepted.connect(self.on_accepted)

    def file_path(self) -> str:
        return self.ui.edit_path.text()

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

        self.accept()
