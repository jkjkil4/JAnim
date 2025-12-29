from __future__ import annotations

import linecache
import os
import re
from functools import wraps
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QDialogButtonBox, QFrame, QLabel,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)

from janim.anims.timeline import Timeline
from janim.exception import GuiCommandError
from janim.gui.utils import apply_popup_flags
from janim.items.item import Item
from janim.locale.i18n import get_translator
from janim.logger import log
from janim.utils.config import Config
from janim.utils.file_ops import get_gui_asset

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.handlers.utils')


def jump(viewer: AnimViewer, command: Timeline.GuiCommand) -> None:
    """
    跳转到该命令执行的 ``global_t``
    """
    tlview = viewer.timeline_view
    tlview.set_progress(tlview.time_to_progress(command.global_t))
    viewer.set_play_state(False)


def parse_item(script: str, locals: dict) -> Item:
    try:
        item = eval(script, {}, locals)
    except Exception:
        QTimer.singleShot(
            0,
            lambda: log.error(_('Failed to parse item from "{script}"').format(script=script))
        )
        raise

    if not isinstance(item, Item):
        raise GuiCommandError(
            _('The {type} object from "{script}" is not a item')
            .format(script=script, type=item.__class__.__name__)
        )

    return item


def get_confirm_buttons(parent: QWidget) -> tuple[QDialogButtonBox, QPushButton, QPushButton]:
    """
    得到通用的确认/取消按钮控件
    """
    btn_box = QDialogButtonBox(parent)
    btn_box.setStandardButtons(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)

    btn_ok = btn_box.button(QDialogButtonBox.StandardButton.Ok)
    btn_ok.setText(_('OK'))

    btn_cancel = btn_box.button(QDialogButtonBox.StandardButton.Cancel)
    btn_cancel.setText(_('Cancel'))

    return (btn_box, btn_ok, btn_cancel)


def get_undo_redo_buttons(
    parent: QWidget,
    on_undo: Callable[[]],
    on_redo: Callable[[]]
) -> tuple[QPushButton, QPushButton]:
    """
    得到通用的撤销/重做按钮控件
    """
    btn_undo = QPushButton(parent)
    btn_undo.setIcon(QIcon(get_gui_asset('undo.png')))
    btn_undo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    btn_redo = QPushButton(parent)
    btn_redo.setIcon(QIcon(get_gui_asset('redo.png')))
    btn_redo.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    sc_undo = QShortcut(QKeySequence('Ctrl+Z'), parent)
    sc_undo.setContext(Qt.ShortcutContext.ApplicationShortcut)

    sc_redo = QShortcut(QKeySequence('Ctrl+Shift+Z'), parent)
    sc_redo.setContext(Qt.ShortcutContext.ApplicationShortcut)

    btn_undo.clicked.connect(on_undo)
    btn_redo.clicked.connect(on_redo)
    sc_undo.activated.connect(on_undo)
    sc_redo.activated.connect(on_redo)

    return (btn_undo, btn_redo)


def slient_runtime_error(func):
    """
    在弹出阻塞框的时候关闭父控件，会输出 ``RuntimeError`` traceback

    使用该装饰器可以忽略抛出的 ``RuntimeError`` 信息
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except RuntimeError:
            pass

    return wrapper


class HandlerPanel(QWidget):
    def __init__(self, viewer: AnimViewer, command: Timeline.GuiCommand):
        super().__init__(viewer)
        self.viewer = viewer
        self.command = command

        self.viewer.before_set_built.connect(self.close)
        self.setWindowTitle(command.text)
        apply_popup_flags(self)

        self.loaded = False

    def update_glw(self) -> None:
        self.viewer.glw.update()

    def update_overlay(self) -> None:
        self.viewer.overlay.update()

    def close_and_rebuild_timeline(self) -> None:
        self.close()
        QTimer.singleShot(0, self.viewer.on_rebuild_triggered)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self.loaded:
            self.load_options()
            self.loaded = True

    def closeEvent(self, event) -> None:
        super().closeEvent(event)

        self.save_options()

    def load_options(self) -> None:
        settings = QSettings(os.path.join(Config.get.temp_dir, 'handler_panel.ini'), QSettings.Format.IniFormat)
        settings.beginGroup(self.viewer.code_file_path)
        monitor: int | None = self.to_int(settings.value(self.setting_key('monitor'), None))
        x: int | None = self.to_int(settings.value(self.setting_key('x'), None))
        y: int | None = self.to_int(settings.value(self.setting_key('y'), None))
        settings.endGroup()

        screens = QApplication.screens()

        if monitor is not None and 0 <= monitor < len(screens):
            self.windowHandle().setScreen(screens[monitor])
        if x is not None and y is not None:
            self.move(x, y)

    def save_options(self) -> None:
        screen = QApplication.screenAt(self.pos())
        screen_index = QApplication.screens().index(screen) if screen else 0

        settings = QSettings(os.path.join(Config.get.temp_dir, 'handler_panel.ini'), QSettings.Format.IniFormat)
        settings.beginGroup(self.viewer.code_file_path)
        settings.setValue(self.setting_key('monitor'), screen_index)
        settings.setValue(self.setting_key('x'), self.x())
        settings.setValue(self.setting_key('y'), self.y())
        settings.endGroup()

    def setting_key(self, name: str) -> str:
        return f'{self.command.name}_{name}'

    def to_int(self, text: str | None) -> int | None:
        return None if text is None else int(text)


class SourceDiff(QFrame):
    """
    显示 ``lineno`` 前后两行的代码，并将修改的代码并排对比
    """

    submitted = Signal()

    def __init__(self, command: Timeline.GuiCommand, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(
            '''
            SourceDiff {
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QLabel {
                font-family: Consolas;
                font-size: 10pt;
            }
            QLabel#delete_label { background-color: #5C1C1C; }
            QLabel#replace_label { background-color: #1C4C1C; }
            '''
        )
        self.command = command

        self.replace_label = QLabel(self)
        self.replace_label.setObjectName('replace_label')
        labels: list[QLabel] = []

        linecache.checkcache(command.filepath)
        self.lines: list[str] = linecache.getlines(command.filepath)
        self.mtime = linecache.cache[command.filepath][1]
        lineno_from = max(1, command.lineno - 2)
        lineno_to = min(len(self.lines), command.lineno + 2)
        for lineno in range(lineno_from, lineno_to + 1):
            line = self.lines[lineno - 1].rstrip()
            label = QLabel(line, self)
            labels.append(label)

            # 给删去的行着色红色
            if lineno == command.lineno:
                label.setObjectName('delete_label')

            # 在删去的行后面紧跟替换的行
            if lineno == command.lineno:
                labels.append(self.replace_label)
                # 正则中大量使用 \s*，这是为了允许在符号之间插入任意的空格
                regex = r'(.*)self\s*\(\s*(["\'])' + re.escape(command.text) + r'\2\s*\)(.*)'
                match = re.fullmatch(regex, line)
                if match is None:
                    raise GuiCommandError(
                        _('Could not find the call site of "{text}". '
                          'Please put the command on a single line and keep the string intact')
                        .format(text=command.text)
                    )
                # group(1): self(...) 之前的内容
                # group(2): 包裹字符串的单引号或双引号
                # group(3): self(...) 之后的内容
                self.match_left = match.group(1)
                self.match_right = match.group(3)

                self.left_spaces = ' ' * len(self.match_left)   # 用于填充多行 replacement 的左侧字符

        vlayout = QVBoxLayout(self)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setSpacing(0)
        for label in labels:
            vlayout.addWidget(label)

        self.setLayout(vlayout)
        self.setMinimumWidth(360)
        self.set_replacement('')

    def set_replacement(self, replacement: str) -> None:
        raw_lines = replacement.split('\n')
        multi_line = len(raw_lines) >= 2

        lines = [
            f'{self.match_left if i == 0 else self.left_spaces}'
            f'{line}'
            f'{"" if multi_line and i == 0 else self.match_right}'
            for i, line in enumerate(raw_lines)
        ]

        self.replace_label.setText('\n'.join(lines))

    @slient_runtime_error
    def submit(self) -> None:
        filepath = self.command.filepath
        lineno = self.command.lineno

        while (new_mtime := os.path.getmtime(filepath)) != self.mtime:
            msgbox = QMessageBox(
                QMessageBox.Icon.Warning,
                _('Confirm Replacement'),
                _('{filename} has been modified.\nDo you want to overwrite it?')
                .format(filename=os.path.basename(filepath)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                self
            )
            msgbox.setDefaultButton(QMessageBox.StandardButton.Yes)
            msgbox.setButtonText(QMessageBox.StandardButton.Yes, _('Yes(&Y)'))
            msgbox.setButtonText(QMessageBox.StandardButton.No, _('No(&N)'))
            ret = msgbox.exec()
            if ret == QMessageBox.StandardButton.No:
                return

            self.mtime = new_mtime

        replaced_lines = self.lines.copy()
        replaced_lines[lineno - 1] = self.replace_label.text() + '\n'

        with open(filepath, 'wt', encoding='utf-8') as f:
            f.write(''.join(replaced_lines))

        self.submitted.emit()
