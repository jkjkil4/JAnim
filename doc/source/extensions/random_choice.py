import uuid

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import ViewList

BTN_TEXT = '🎲 随机切换'


# 用来让 gettext 提取文本用的
class i18n_message(nodes.paragraph):
    pass


class random_choice(nodes.General, nodes.Element):
    pass


class random_option(nodes.General, nodes.Element):
    pass


class unwrap_random_options(nodes.General, nodes.Element):
    pass


def visit_i18n_message_html(self, node):
    raise nodes.SkipNode


def visit_random_choice_html(self, node):
    button_text = BTN_TEXT
    start_text = ''

    for child in node.children:
        if isinstance(child, i18n_message):
            match child['msg_type']:
                case 'button':
                    button_text = child.astext()
                case 'start-text':
                    start_text = child.astext()

    self.body.append(
        f'<div class="random-choice" id="{node["id"]}" destroy="{int(node["destroy"])}">'
    )
    if start_text:
        self.body.append(f'<div class="random-placeholder">{start_text}</div>')

    node['final_button_text'] = button_text


def depart_random_choice_html(self, node):
    btn_text = node.get('final_button_text', BTN_TEXT)
    self.body.append(f'<button class="random-button">{btn_text}</button></div>')


def visit_random_option_html(self, node):
    self.body.append('<div class="random-item" style="display:none;"><template>')


def depart_random_option_html(self, node):
    self.body.append('</template><div class="lazy-random-item-content"></div></div>')


def visit_unwrap_random_options_html(self, node):
    self.body.append('<div class="unwrap-random-options">')


def depart_unwrap_random_options_html(self, node):
    self.body.append('</div>')


class RandomChoiceDirective(Directive):
    has_content = True
    option_spec = {
        'start-text': str,
        'destroy': bool,
    }

    def run(self):
        node = random_choice()
        node['id'] = f'random-{uuid.uuid4().hex[:8]}'
        node['destroy'] = 'destroy' in self.options

        # 让 start-text 能被 gettext 提取
        if 'start-text' in self.options:
            text = self.options.get('start-text')

            msg_node = i18n_message()
            msg_node['msg_type'] = 'start-text'

            rst = ViewList()
            for line in text.splitlines():
                rst.append(line, source='<random-choice-option>')
            self.state.nested_parse(rst, 0, msg_node)

            node += msg_node

        # 让 按钮文本 能被 gettext 提取
        default_btn = '🎲 随机切换'
        btn_node = i18n_message()
        btn_node['msg_type'] = 'button'

        rst_btn = ViewList()
        rst_btn.append(default_btn, source='<random-choice-ui>')
        self.state.nested_parse(rst_btn, 0, btn_node)

        node += btn_node

        # 解析内部内容
        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


class RandomOptionDirective(Directive):
    has_content = True

    def run(self):
        node = random_option()
        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


class UnwrapRandomOptionsDirective(Directive):
    has_content = True

    def run(self):
        node = unwrap_random_options()
        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


def setup(app):
    app.add_node(i18n_message, html=(visit_i18n_message_html, None))

    app.add_node(random_choice, html=(visit_random_choice_html, depart_random_choice_html))
    app.add_node(random_option, html=(visit_random_option_html, depart_random_option_html))
    app.add_node(
        unwrap_random_options,
        html=(visit_unwrap_random_options_html, depart_unwrap_random_options_html),
    )

    app.add_directive('random-choice', RandomChoiceDirective)
    app.add_directive('random-option', RandomOptionDirective)
    app.add_directive('unwrap-random-options', UnwrapRandomOptionsDirective)

    # 添加 JS
    app.add_js_file(
        None,
        body=R"""
        document.addEventListener("DOMContentLoaded", () => {
            document.querySelectorAll(".random-choice").forEach(container => {
                const items = Array.from(container.querySelectorAll(".random-item"));
                const button = container.querySelector(".random-button");
                const placeholder = container.querySelector(".random-placeholder");
                const destroy = container.getAttribute('destroy') === "1";

                let current = -1;
                let firstShown = true;
                let unseen = items.map((_, idx) => idx);

                function showRandom() {
                    if (placeholder)
                        placeholder.style.display = "none";

                    if (current >= 0 && current < items.length) {
                        const prevItem = items[current];
                        prevItem.querySelectorAll("video").forEach(v => {
                            v.pause();
                            v.currentTime = 0;
                        });

                        if (destroy) {
                            const lazyContent = prevItem.querySelector('.lazy-random-item-content');
                            if (lazyContent) lazyContent.innerHTML = '';
                        }
                    }

                    items.forEach(el => el.style.display = 'none');

                    // 随机选择一个
                    let next;
                    if (unseen.length > 0) {
                        const idx = Math.floor(Math.random() * unseen.length);
                        next = unseen[idx];
                        unseen.splice(idx, 1);
                    } else {
                        do { next = Math.floor(Math.random() * items.length); }
                        while (next === current && items.length > 1);
                    }

                    const item = items[next];

                    // 如果 lazy-random-item-content 为空，则搬移 <template> 内容
                    const lazyContent = item.querySelector('.lazy-random-item-content');
                    const template = item.querySelector('template');
                    if (lazyContent && template && lazyContent.innerHTML.trim() === '') {
                        lazyContent.innerHTML = template.innerHTML;
                    }

                    item.style.display = 'block';
                    current = next;

                    // 除第一次外，自动播放该 item 中的视频
                    if (!firstShown) {
                        item.querySelectorAll("video").forEach(v => {
                            v.currentTime = 0;
                            v.play();
                            // v.play().catch(() => {});
                        });
                    } else {
                        firstShown = false;
                    }
                }

                button.addEventListener("click", showRandom);
                if (!placeholder) {
                    showRandom();
                }
            });
            document.querySelectorAll(".unwrap-random-options").forEach(container => {
                const items = Array.from(container.querySelectorAll(".random-item"));

                items.forEach(item => {
                    // const lazyContent = item.querySelector('.lazy-random-item-content');
                    const template = item.querySelector('template');
                    item.innerHTML = template.innerHTML;
                    item.style.display = 'block';
                });
            });
        });
        """,
    )
    return {'parallel_read_safe': True, 'parallel_write_safe': True}
