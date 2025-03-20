import locale
import os
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from janim.locale.i18n import get_local_strings
from janim.utils.file_ops import get_janim_dir
from janim.utils.font.database import get_database

if TYPE_CHECKING:
    from fontTools.ttLib.tables._n_a_m_e import NameRecord

_ = get_local_strings('font_table')


class FontTable(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setup_ui()
        self.setWindowTitle(_('Font List'))
        self.resize(760, 640)

    def setup_ui(self) -> None:
        self.label = QLabel()
        self.label.setScaledContents(True)
        self.label.setPixmap(QPixmap(os.path.join(get_janim_dir(), 'gui', 'functions/search.png')))

        self.searcher = QLineEdit()
        self.searcher.setMinimumWidth(260)
        self.searcher.textEdited.connect(self.on_searcher_edited)

        self.table = QTableWidget()
        self.setup_table(self.table)

        self.top_layout = QHBoxLayout()
        self.top_layout.addWidget(self.label)
        self.top_layout.addWidget(self.searcher)
        self.top_layout.addStretch(1)

        self.main_layout = QVBoxLayout()
        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addWidget(self.table)

        self.setLayout(self.main_layout)

    @staticmethod
    def setup_table(table: QTableWidget) -> None:
        db = get_database()
        infos = [
            info
            for family in db.family_by_name.values()
            for info in family.infos
        ]
        table.setRowCount(len(infos))
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels((_('Family Name'),
                                         _('Full Name'),
                                         _('Display Name (includes multiple languages, make good use of search)')))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)

        for row, info in enumerate(infos):
            records: list[NameRecord] = [
                record
                for record in info.name.names
                if record.nameID == 1
            ]
            records.sort(key=lambda x: x.langID, reverse=True)

            names = []

            for record in records:
                platform_id = record.platformID
                language_id = record.langID
                displayname = record.string.decode('utf-16-be' if record.isUnicode() else 'latin-1')
                names.append(f'({platform_id},{locale.windows_locale.get(language_id, language_id)}){displayname}')

            contents = (
                info.family_name,
                info.full_name,
                ', '.join(names)
            )
            for col, content in enumerate(contents):
                item = QTableWidgetItem(content)
                table.setItem(row, col, item)

    @staticmethod
    def is_substr(sub: str, text: str) -> bool:
        sub = sub.lower()
        text = text.lower()
        idx = 0
        for char in sub:
            try:
                idx = text.index(char, idx) + 1
            except ValueError:
                return False
        return True

    def on_searcher_edited(self, text: str) -> None:
        rows = self.table.rowCount()
        cols = self.table.columnCount()

        if not text:
            for row in range(rows):
                self.table.showRow(row)
            return

        for row in range(rows):
            if any(self.is_substr(text, self.table.item(row, col).text()) for col in range(cols)):
                self.table.showRow(row)
            else:
                self.table.hideRow(row)
