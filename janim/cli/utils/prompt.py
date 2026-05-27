import enum
import itertools as it
import sys
from dataclasses import dataclass
from typing import Any

from rich.align import AlignMethod
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
    console: Console,
    entries: list[Entry],
    *,
    subtitle: str | None = None,
    subtitle_align: AlignMethod = 'center',
) -> list[Panel]:
    # 4 来自 Panel 边框的两个像素以及其内部横向 padding 的两个像素
    pages = get_pages(console, entries, 4)
    total_pages = len(pages)

    key_hint = '' if total_pages == 1 else ' ↑/↓'

    panels = [
        Panel(
            page,
            title=f'Page {i}/{total_pages}{key_hint}',
            subtitle=subtitle,
            height=ENTRIES_COLUMN_HEIGHT + 2,
            subtitle_align=subtitle_align,
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

    key_hint = '' if total_pages == 1 else ' ↑/↓'

    panels = [
        Panel(
            page,
            title=f'Page {i}/{total_pages}{key_hint}',
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


def prompt_panels(
    console: Console, panels: list[Panel], prompt: str, *, auto_completes: list[str] | None = None
) -> str | None:
    texts = capture_panels(console, panels)
    single_page = len(texts) == 1

    # 在只有一页的时候先输出可选项，再加载 prompt-toolkit
    if single_page:
        print(texts[0], end='', file=sys.stderr)

    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding.key_bindings import KeyBindings
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import HSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.output import create_output
    from prompt_toolkit.widgets import TextArea

    input_box = TextArea(
        prompt=prompt,
        multiline=False,
        height=1,
    )

    if single_page:
        root_element = input_box
    else:
        display_control = FormattedTextControl()
        # +2 来源于 Panel 的上下边线
        display_window = Window(content=display_control, height=ENTRIES_COLUMN_HEIGHT + 2)

        root_element = HSplit([display_window, input_box])

    kb = KeyBindings()
    page = 0

    if auto_completes is not None:
        register_auto_complete(kb, input_box, auto_completes)

    @kb.add('c-c')
    def _interrupt(event) -> None:
        event.app.exit(result=None)

    @kb.add('enter')
    def _confirm(event) -> None:
        user_input = input_box.text
        event.app.exit(result=user_input)

    if not single_page:

        @kb.add('up')
        def _prev(event) -> None:
            nonlocal page
            page = (page - 1) % len(panels)
            redraw()

        @kb.add('down')
        def _next(event) -> None:
            nonlocal page
            page = (page + 1) % len(panels)
            redraw()

        def redraw() -> None:
            display_control.text = texts[page]  # type: ignore

        redraw()

    app = Application(
        layout=Layout(root_element, focused_element=input_box),
        key_bindings=kb,
        output=create_output(stdout=sys.stderr),
    )
    return app.run()


# 虽然 prompt-toolkit 有内置的 Completer，但这里还是手写了，自己处理了一下逗号分割
def register_auto_complete(kb, input_box, auto_completes: list[str]) -> None:
    # (prefix, match_index) 当前的匹配状态
    auto_complete_state: tuple[str, int] | None = None

    @kb.add('tab')
    def _auto_complete(event) -> None:
        nonlocal auto_complete_state

        user_input = input_box.text
        try:
            last_comma = user_input.rindex(',')
            last_start = last_comma + 1
        except ValueError:
            last_start = 0

        last_part = user_input[last_start:]

        # 仅在非空且非数值时才进行自动补全
        if not last_part or last_part.isnumeric():
            return

        new_auto_complete_state = None
        replace_by = last_part

        # 在没有上一次匹配时，将当前最后一部分的内容作为匹配前缀，在 auto_completes 中从头开始搜索
        if auto_complete_state is None:
            prefix = last_part
            for idx, pattern in enumerate(auto_completes):
                if pattern.startswith(prefix):
                    new_auto_complete_state = (prefix, idx)
                    replace_by = pattern
                    break
        # 在有上一次匹配时，沿用上一次的匹配前缀，从上一次的匹配项往后搜索
        else:
            prefix, prev_match_index = auto_complete_state
            start = prev_match_index + 1
            length = len(auto_completes)
            for i in range(start, start + length):
                idx = i % length
                pattern = auto_completes[idx]
                if pattern.startswith(prefix):
                    new_auto_complete_state = (prefix, idx)
                    replace_by = pattern
                    break

        new_text = user_input[:last_start] + replace_by
        input_box.text = new_text
        input_box.buffer.cursor_position = len(new_text)
        auto_complete_state = new_auto_complete_state

    # 当文本变化时清空匹配状态
    def on_text_changed(_) -> None:
        nonlocal auto_complete_state
        auto_complete_state = None

    input_box.buffer.on_text_changed += on_text_changed


class MatchState(enum.Enum):
    Matched = 0
    InvalidNumber = 1
    InvalidKeyword = 2


@dataclass
class MatchResult:
    state: MatchState

    # Matched -> metadata (Any)
    # InvalidNumber -> order (int)
    # InvalidKeyword -> keyword (str)
    data: Any | int | str


def parse_user_input(entries: list[Entry], user_input: str) -> list[MatchResult]:
    results: list[MatchResult] = []

    for split_str in user_input.replace(' ', '').split(','):
        if not split_str:
            continue
        if split_str.isnumeric():
            idx = int(split_str) - 1
            if 0 <= idx < len(entries):
                results.append(MatchResult(MatchState.Matched, entries[idx].metadata))
            else:
                results.append(MatchResult(MatchState.InvalidNumber, idx + 1))
        else:
            for entry in entries:
                if entry.text == split_str:
                    results.append(MatchResult(MatchState.Matched, entry.metadata))
                    break
            else:
                results.append(MatchResult(MatchState.InvalidKeyword, split_str))

    return results


def prompt_entries(
    entries: list[Entry],
    prompt: str,
    *,
    subtitle: str | None = None,
    subtitle_align: AlignMethod = 'center',
) -> list[MatchResult]:
    console = Console()
    panels = get_panels(console, entries, subtitle=subtitle, subtitle_align=subtitle_align)
    user_input = prompt_panels(
        console, panels, prompt, auto_completes=[entry.text for entry in entries]
    )
    if user_input is None:
        return []

    return parse_user_input(entries, user_input)


def prompt_entries_in_categories(
    categories: list[Category],
    prompt: str,
) -> list[MatchResult]:
    entries = list(it.chain.from_iterable(category.entries for category in categories))

    console = Console()
    panels = get_panels_in_categories(console, categories)
    user_input = prompt_panels(
        console, panels, prompt, auto_completes=[entry.text for entry in entries]
    )
    if user_input is None:
        return []

    return parse_user_input(entries, user_input)
