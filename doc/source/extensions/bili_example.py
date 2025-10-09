from docutils import nodes
from docutils.parsers.rst import Directive


class bili_example(nodes.General, nodes.Element):
    pass


def visit_bili_html(self, node):
    url = node['url']
    title = node['title']

    header_content = f'<span>{title}</span>'
    if node['author']:
        header_content += f'<span style="font-size: 0.8rem;">by {node["author"]}</span>'

    self.body.append(f'''
    <div class="janim-box">
        <div class="bili-video-content">
            <iframe style="position: absolute; width: 100%; height: 100%; left: 0; top: 0;"
                src="{url}" frameborder="no" scrolling="no"></iframe>
        </div>
        <h5 class="example-header line", style="margin-top: 0; margin-bottom: 0;">
            {header_content}
        </h5>
    ''')

    if node['source-link']:
        self.body.append(f'''
        <div class="example-source-link">
            源码：
            <a href="{node['source-link']}" target="_blank">{node['source-link']}</a>
        </div>
        ''')

    if node['has_content']:
        self.body.append('<div class="janim-content">')


def depart_bili_html(self, node):
    if node['has_content']:
        self.body.append('</div>')
    self.body.append('</div>')


class BiliExampleDirective(Directive):
    has_content = True
    required_arguments = 1
    option_spec = {
        'title': str,
        'author': str,
        'source-link': str,
    }

    def run(self):
        url = self.arguments[0]
        node = bili_example()
        node['url'] = url
        node['title'] = self.options.get('title')
        node['author'] = self.options.get('author')
        node['source-link'] = self.options.get('source-link')
        node['has_content'] = bool(self.content)
        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


def setup(app):
    app.add_node(
        bili_example,
        html=(visit_bili_html, depart_bili_html),
    )
    app.add_directive("bili-example", BiliExampleDirective)
    return {'parallel_read_safe': True, 'parallel_write_safe': True}
