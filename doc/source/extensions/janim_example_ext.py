import ast
import os
from functools import lru_cache
from pathlib import Path

import jinja2
from docutils.parsers.rst import Directive
from janim.utils.file_ops import get_janim_dir


class JAnimExampleDirective(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    option_spec = {
        # 指定类名提取代码作为 content，若指定但缺省内容则使用主参数
        'extract-from-test': str,
        # 提取 "# beginmark xxx" 与 "# endmark xxx" 之间的代码作为 content，若指定但缺省内容则使用主参数
        'extract-from-test-mark': str,
        # 媒体文件路径，可以是图片或者视频，以 source/ 目录为根目录
        'media': str,
        # 忽略，仅用于在代码 docstring 写一个链接方便用户跳转
        'url': str,     # ignores
        # 在底部显示一些额外的内容，例如可以另行参考的内容
        'ref': str,
        # 若指定则不显示名称
        'hide_name': bool,
        # 若指定则不显示代码
        'hide_code': bool,
    }
    final_argument_whitespace = True

    def run(self):
        scene_name = self.arguments[0]
        media_url = self.options["media"]
        hide_name = 'hide_name' in self.options
        hide_code = 'hide_code' in self.options

        if 'extract-from-test' in self.options:
            classname = self.options['extract-from-test']
            if classname == 'None':     # wtf 'None' instead of None
                classname = scene_name
            file_path = get_examples_of_animations_path()
            source = get_classdefs(file_path)[classname]
            content = ['from janim.imports import *', '', *source.splitlines()]
        elif 'extract-from-test-mark' in self.options:
            markname = self.options['extract-from-test-mark']
            if markname == 'None':     # wtf 'None' instead of None
                markname = scene_name
            file_path = get_examples_of_animations_path()
            source = get_marked_source(file_path, markname)
            content = ['from janim.imports import *', '', *source.splitlines()]
        else:
            content = self.content

        env = self.state.document.settings.env
        source_file = Path(env.doc2path(env.docname, base=None))
        source_dir = source_file.parent
        root_dir = Path(env.app.srcdir)
        media_url = os.path.relpath(root_dir / media_url, root_dir / source_dir).replace('\\', '/')

        if any(media_url.endswith(ext) for ext in ['.png', '.jpg', '.gif']):
            is_video = False
        else:
            is_video = True

        source_block = [
            ".. code-block:: python",
            "",
            *["    " + line for line in content]
        ]
        source_block = '\n'.join(source_block)

        state_machine = self.state_machine
        document = state_machine.document

        rendered_template = jinja2.Template(TEMPLATE).render(
            scene_name=scene_name,
            scene_name_lowercase=scene_name.lower(),
            media_url=media_url,
            source_block=source_block,
            ref=self.options.get('ref', ''),

            is_video=is_video,
            hide_name=hide_name,
            hide_code=hide_code
        )

        state_machine.insert_input(
            rendered_template.split('\n'),
            source=document.attributes['source']
        )

        return []


def setup(app):
    app.add_directive('janim-example', JAnimExampleDirective)

    metadata = {'parallel_read_safe': False, 'parallel_write_safe': True}
    return metadata


TEMPLATE = R'''
.. raw:: html

    <div class="janim-box">

{% if is_video %}
        <video id="{{ scene_name_lowercase }}" class="janim-video" controls src="{{ media_url }}"></video>
{% else %}
.. image:: {{ media_url }}
    :align: center
    :name: {{ scene_name_lowercase }}
{% endif %}

{% if not hide_name %}
.. raw:: html

        <h5 class="example-header">
            {{ scene_name }}
            <a class="headerlink" href="#{{ scene_name_lowercase }}">¶</a>
        </h5>
{% endif %}

{% if not hide_code %}
{{ source_block }}
{% endif %}

{% if ref %}
.. container:: example-ref

    .. rst-class:: example-ref-prefix

    参考：

    {{ ref }}

{% endif %}

.. raw:: html

    </div>
'''


@lru_cache(maxsize=1)
def get_examples_of_animations_path() -> str:
    return os.path.join(get_janim_dir(), '..', 'test', 'examples', 'examples_of_animations.py')


@lru_cache(maxsize=None)
def get_classdefs(file_path: str) -> dict[str, str]:
    """
    使用 AST 提取指定文件中，在顶层（toplevel）直接定义的 ``class`` 源码
    """
    with open(file_path, encoding='utf-8') as f:
        source = f.read()

    if not source:
        return {}

    tree = ast.parse(source, filename=file_path)

    classdefs = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    return {
        node.name: segment
        for node in classdefs
        if (segment := ast.get_source_segment(source, node)) is not None
    }


@lru_cache(maxsize=None)
def get_marked_source(file_path: str, markname: str) -> str:
    begin_marker = f'# beginmark {markname}'
    end_marker = f'# endmark {markname}'

    with open(file_path, encoding='utf-8') as f:
        lines = f.readlines()

    begin_line = None
    end_line = None

    for index, line in enumerate(lines):
        stripped = line.strip()
        if begin_line is None and stripped == begin_marker:
            begin_line = index
            continue

        if begin_line is not None and (stripped == end_marker or stripped.startswith(end_marker)):
            end_line = index
            break

    if begin_line is None:
        raise KeyError(f'Cannot find begin mark: {begin_marker}')
    if end_line is None:
        raise KeyError(f'Cannot find end mark: {end_marker}')
    if end_line <= begin_line:
        raise ValueError(f'Invalid mark range: {markname}')

    return ''.join(lines[begin_line + 1:end_line]).rstrip('\n')
