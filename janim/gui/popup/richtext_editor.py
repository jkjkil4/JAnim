
import re

from bs4 import BeautifulSoup, Tag
from PySide6.QtCore import QMimeData, Signal
from PySide6.QtGui import QColor, QSyntaxHighlighter
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QVBoxLayout, QWidget

from janim.gui.utils.text_edit import TextEdit
from janim.locale.i18n import get_translator

_ = get_translator('janim.gui.popup.richtext_editor')


class RichTextEditor(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setup_ui()
        self.setWindowTitle(_('Rich Text Editor'))
        self.resize(600, 400)
        self.check_box_wordwrap.setChecked(True)

    def setup_ui(self):
        self.check_box_wordwrap = QCheckBox(_('Word wrap'))
        self.check_box_wordwrap.stateChanged.connect(
            lambda state: self.editor.setLineWrapMode(RichTextEdit.LineWrapMode.WidgetWidth
                                                      if state
                                                      else RichTextEdit.LineWrapMode.NoWrap)
        )
        self.check_box_wordwrap.setChecked(False)

        self.check_box_html = QCheckBox(_('Recognize rich text format on paste'))
        self.check_box_html.stateChanged.connect(self.check_box_html_state_changed)

        self.editor = RichTextEdit()
        self.editor.html_inserted.connect(lambda: self.check_box_html.setChecked(False))

        self.hlayout = QHBoxLayout()
        self.hlayout.addStretch()
        self.hlayout.addWidget(self.check_box_wordwrap)
        self.hlayout.addWidget(self.check_box_html)

        self.vlayout = QVBoxLayout()
        self.vlayout.addLayout(self.hlayout)
        self.vlayout.addWidget(self.editor)

        self.setLayout(self.vlayout)

    def check_box_html_state_changed(self, state: bool) -> None:
        self.editor.convert_html = state


class RichTextEdit(TextEdit):
    html_inserted = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.highlighter = RichTextHighlighter(self.document())

        self.resize(600, 400)

        self.convert_html = False

    def insertFromMimeData(self, source: QMimeData) -> None:
        if self.convert_html and source.hasHtml():
            self.insertPlainText(self.html2richtext(source.html()))
            self.html_inserted.emit()
        else:
            self.insertPlainText(source.text())

    @staticmethod
    def html2richtext(html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        return RichTextEdit.parse_node(soup.find('html').find('body'))

    @staticmethod
    def parse_node(node: Tag) -> str:
        ret = []
        has_div = False
        for child in node.children:
            if not child:
                continue

            match child.name:
                case 'div':
                    ret.append(RichTextEdit.parse_node(child))
                    has_div = True
                case 'span':
                    ret.append(RichTextEdit.parse_span(child))
                case 'br':
                    ret.append('')
                case _:
                    if child.text:
                        ret.append(RichTextEdit.parse_text(child.text))

        return ('\n' if has_div else '').join(ret)

    @staticmethod
    def parse_span(span: Tag) -> str:
        if span.text.isspace():
            style = None
        else:
            style = RichTextEdit.parse_style(span.get('style', ''))

        return (
            f'<fc {RichTextEdit.parse_color(style['color'])}>{RichTextEdit.parse_text(span.text)}</fc>'
            if style is not None and 'color' in style
            else RichTextEdit.parse_text(span.text)
        )

    @staticmethod
    def parse_color(color: str) -> str:
        if color.startswith('#'):
            return color

        if color.startswith('rgb(') and color.endswith(')'):
            rgb = color.lstrip('rgb(').rstrip(')').split(',')
            return ' '.join([
                str(round(float(v) / 255, 2))
                for v in rgb
            ])

        if color.startswith('rgba(') and color.endswith(')'):
            rgba = color.lstrip('rgba(').rstrip(')').split(',')
            return ' '.join([
                str(round(float(v) / 255, 2))
                for v in rgba[:3]
            ]) + f' {rgba[3]}'

        return color

    @staticmethod
    def parse_style(style: str) -> dict[str, str]:
        ret = {}
        for pair in style.split(';'):
            split = pair.split(':')
            if len(split) != 2:
                continue
            key, value = split
            ret[key.strip()] = value.strip()
        return ret

    @staticmethod
    def parse_text(text: str) -> str:
        return text.replace('<', '<<')


class RichTextHighlighter(QSyntaxHighlighter):
    regex = re.compile(r'<<|<(\/?[^>]*)>')
    escape_color1 = QColor(130, 130, 130)
    escape_color2 = QColor(249, 183, 117)
    act_color = QColor(86, 156, 214)

    def highlightBlock(self, text: str) -> None:
        iter = re.finditer(self.regex, text)
        for match in iter:
            match: re.Match
            start, end = match.span()
            groups = match.groups()

            if groups[0] is None:   # <<
                self.setFormat(start, 1, self.escape_color1)
                self.setFormat(start + 1, 1, self.escape_color2)
            else:
                self.setFormat(start, end - start, self.act_color)
