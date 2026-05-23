from dataclasses import dataclass
import itertools as it
from typing import Any

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

ENTRIES_COLUMN_HEIGHT = 4
ENTRIES_PADDING = 3


@dataclass
class Entry:
    text: str
    metadata: Any | None


@dataclass
class Category:
    name: str
    entries: list[Entry]


def get_pages(
    console: Console, entries: list[Entry], page_padding: int, *, start: int = 1
) -> list[Columns]:
    if not entries:
        return []

    column_texts = [
        Text(
            '\n'.join(f'{i:02}: {entry.text}' for i, entry in column_entries),
        )
        for column_entries in it.batched(enumerate(entries, start=start), ENTRIES_COLUMN_HEIGHT)
    ]
    column_widths = [console.measure(text).maximum for text in column_texts]

    max_width = console.width - page_padding
    current_width: int = -ENTRIES_PADDING
    cells: list[Text] = []

    pages: list[Columns] = []

    def add_cell(text: Text, width: int) -> bool:
        nonlocal current_width
        new_width = current_width + ENTRIES_PADDING + width
        if new_width > max_width and cells:  # 最后的 and cells 保证每页至少有一个
            return False
        current_width = new_width
        cells.append(text)
        return True

    def pagebreak() -> None:
        nonlocal current_width
        pages.append(
            Columns(
                cells,
                padding=(0, ENTRIES_PADDING),
                # 按理来说 columns 的宽度不会超过 max_width
                # 并且我们不使用 expand=True
                # 所以这里不给 Columns 设置 width
            )
        )
        current_width = -ENTRIES_PADDING
        cells.clear()

    for text, width in zip(column_texts, column_widths):
        if not add_cell(text, width):
            pagebreak()
            add_cell(text, width)

    pagebreak()
    return pages


def get_panels(
    console: Console, entries: list[Entry], *, subtitle: str | None = None
) -> list[Panel]:
    # 4 来自 Panel 边框的两个像素以及其内部横向 padding 的两个像素
    pages = get_pages(console, entries, 4)
    total_pages = len(pages)

    panels = [
        Panel(
            page,
            title=f'Page {i}/{total_pages}',
            subtitle=subtitle,
            height=ENTRIES_COLUMN_HEIGHT + 2,
        )
        for i, page in enumerate(pages, start=1)
    ]
    return panels


def get_panels_in_categories(
    console: Console,
    categories: list[Category],
) -> list[Panel]:
    pages_with_category_name: list[tuple[Columns, str]] = []
    start = 1
    for category in categories:
        # 4 来自 Panel 边框的两个像素以及其内部横向 padding 的两个像素
        for page in get_pages(console, category.entries, 4, start=start):
            pages_with_category_name.append((page, category.name))
        start += len(category.entries)

    total_pages = len(pages_with_category_name)

    panels = [
        Panel(
            page,
            title=f'Page {i}/{total_pages}',
            subtitle=category,
            height=ENTRIES_COLUMN_HEIGHT + 2,
        )
        for i, (page, category) in enumerate(pages_with_category_name, start=1)
    ]
    return panels


def capture_panels(console: Console, panels: list[Panel]) -> list[str]:
    texts: list[str] = []
    for panel in panels:
        with console.capture() as capture:
            console.print(panel)
        texts.append(capture.get())
    return texts


def prompt_panels(console: Console, panels: list[Panel], prompt: str) -> str | None:
    texts = capture_panels(console, panels)

    display_control = FormattedTextControl()
    # +2 来源于 Panel 的上下边线
    display_window = Window(content=display_control, height=ENTRIES_COLUMN_HEIGHT + 2)

    input_box = TextArea(
        prompt=prompt,
        multiline=False,
        height=1,
    )

    root_container = HSplit([display_window, input_box])

    kb = KeyBindings()
    page = 0

    @kb.add('up')
    def _prev(event) -> None:
        nonlocal page
        page = max(0, page - 1)
        redraw()

    @kb.add('down')
    def _next(event) -> None:
        nonlocal page
        page = min(len(panels) - 1, page + 1)
        redraw()

    @kb.add('c-c')
    def _interrupt(event) -> None:
        event.app.exit(result=None)

    @kb.add('enter')
    def _confirm(event) -> None:
        user_input = input_box.text
        event.app.exit(result=user_input)

    def redraw() -> None:
        display_control.text = texts[page]

    redraw()

    app = Application(
        layout=Layout(root_container, focused_element=input_box),
        key_bindings=kb,
    )
    return app.run()


def prompt_entries(entries: list[Entry], prompt: str) -> list[Any]:
    console = Console()
    panels = get_panels(console, entries)
    user_input = prompt_panels(console, panels, prompt)
    print(user_input)


def prompt_entries_in_categories(categories: list[Category], prompt: str) -> list[Any]:
    console = Console()
    panels = get_panels_in_categories(console, categories)
    user_input = prompt_panels(console, panels, prompt)
    print(user_input)


import janim.examples as examples
from janim.cli.execute import get_all_timelines_from_module

timeline_types = get_all_timelines_from_module(examples)
timeline_entries = [Entry(type.__name__, type) for type in timeline_types]

console = Console()
categories = [Category('JAnim Examples', timeline_entries), Category('test', timeline_entries)]

prompt_entries_in_categories(categories, 'Select: ')
