from docutils import nodes
from docutils.parsers.rst import Directive
import uuid


class random_choice(nodes.General, nodes.Element):
    pass


class random_option(nodes.General, nodes.Element):
    pass


class unwrap_random_options(nodes.General, nodes.Element):
    pass


def visit_random_choice_html(self, node):
    self.body.append(f'<div class="random-choice" id="{node["id"]}">')
    if node.get("start-text"):
        self.body.append(f'<div class="random-placeholder">{node["start-text"]}</div>')


def depart_random_choice_html(self, node):
    self.body.append('<button class="random-button">🎲 随机切换</button></div>')


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
        'start-text': str
    }

    def run(self):
        # env = self.state.document.settings.env
        node = random_choice()
        node['id'] = f"random-{uuid.uuid4().hex[:8]}"
        node['start-text'] = self.options.get('start-text')
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
    app.add_node(random_choice,
                 html=(visit_random_choice_html, depart_random_choice_html))
    app.add_node(random_option,
                 html=(visit_random_option_html, depart_random_option_html))
    app.add_node(unwrap_random_options,
                 html=(visit_unwrap_random_options_html, depart_unwrap_random_options_html))
    app.add_directive("random-choice", RandomChoiceDirective)
    app.add_directive("random-option", RandomOptionDirective)
    app.add_directive("unwrap-random-options", UnwrapRandomOptionsDirective)

    # 添加 JS
    app.add_js_file(None, body=R"""
    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll(".random-choice").forEach(container => {
            const items = Array.from(container.querySelectorAll(".random-item"));
            const button = container.querySelector(".random-button");
            const placeholder = container.querySelector(".random-placeholder");
            let current = -1;
            let firstShown = true;

            function showRandom() {
                if (placeholder)
                    placeholder.style.display = "none";

                if (current >= 0 && current < items.length) {
                    const prevItem = items[current];
                    prevItem.querySelectorAll("video").forEach(v => {
                        v.pause();
                        v.currentTime = 0;
                    });
                }

                items.forEach(el => el.style.display = 'none');

                // 随机选择一个
                let next;
                do { next = Math.floor(Math.random() * items.length); }
                while (next === current && items.length > 1);

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
    """)
    return {'parallel_read_safe': True, 'parallel_write_safe': True}
