"""
该 extention 仅作用于 gettext 流程中，
将所有的 “基类：...” 文本从翻译文件中剔除（因为这些文本 sphinx 自身就会进行翻译）
"""

from __future__ import annotations

import re
from typing import Iterable

from docutils import nodes
from sphinx import addnodes
from sphinx.application import Sphinx


_BASES_PREFIX_RE = re.compile(r"^\s*基类：\s*")


def _iter_class_desc_contents(doctree: nodes.document) -> Iterable[addnodes.desc_content]:
    for desc in doctree.findall(addnodes.desc):
        if desc.get("objtype") != "class":
            continue
        for child in desc:
            if isinstance(child, addnodes.desc_content):
                yield child


def _strip_class_bases_for_gettext(app: Sphinx, doctree: nodes.document) -> None:
    # 仅在 gettext builder 下处理
    if app.builder is None or app.builder.name != "gettext":
        return

    for content in _iter_class_desc_contents(doctree):
        # 通常 "基类：" 是 desc_content 里的一个 paragraph
        for para in list(content.findall(nodes.paragraph)):
            text = para.astext().strip()
            if _BASES_PREFIX_RE.match(text):
                para.parent.remove(para)


def setup(app: Sphinx) -> dict[str, bool]:
    app.connect("doctree-read", _strip_class_bases_for_gettext)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
