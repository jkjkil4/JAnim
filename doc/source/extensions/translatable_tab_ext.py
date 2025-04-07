from sphinx_tabs.tabs import (SphinxDirective, SphinxTabsPanel, SphinxTabsTab,
                              get_compatible_builders, nodes)


def visit(translator, node):
    # Borrowed from `sphinx-inline-tabs`
    attrs = node.attributes.copy()
    attrs.pop("classes")
    attrs.pop("ids")
    attrs.pop("names")
    attrs.pop("dupnames")
    attrs.pop("backrefs")
    text = translator.starttag(node, node.tagname, **attrs)
    translator.body.append(text.strip())


def depart(translator, node):
    translator.body.append(f"</{node.tagname}>")


# modified from sphinx_tabs.tabs.TabDirective
class TranslatableTabDirective(SphinxDirective):
    """Tab directive, for adding a tab to a collection of tabs"""

    has_content = True

    def __init__(self, *args, **kwargs):
        self.tab_id = None
        self.tab_classes = set()
        super().__init__(*args, **kwargs)

    def run(self):
        """Parse a tab directive"""
        self.assert_has_content()

        tabs_id = self.env.temp_data["tabs_stack"][-1]
        tabs_key = f"tabs_{tabs_id}"

        include_tabs_id_in_data_tab = False
        if self.tab_id is None:
            tab_id = self.env.new_serialno(tabs_key)
            include_tabs_id_in_data_tab = True
        else:
            tab_id = self.tab_id

        tab_name = SphinxTabsTab()
        self.state.nested_parse(self.content[0:1], 0, tab_name)
        # Remove the paragraph node that is created by nested_parse
        # 不，别 remove，我魔改了这两行
        # tab_name.children[0].replace_self(tab_name.children[0].children)
        tab_name.children[0]["classes"] = ["tab-p"]

        tab_name["classes"].append("sphinx-tabs-tab")
        tab_name["classes"].extend(sorted(self.tab_classes))

        i = 1
        while tab_id in self.env.temp_data[tabs_key]["tab_ids"]:
            tab_id = f"{tab_id}-{i}"
            i += 1
        self.env.temp_data[tabs_key]["tab_ids"].append(tab_id)

        data_tab = str(tab_id)
        if include_tabs_id_in_data_tab:
            data_tab = f"{tabs_id}-{data_tab}"

        self.env.temp_data[tabs_key]["tab_titles"].append((data_tab, tab_name))

        panel = SphinxTabsPanel()
        panel["role"] = "tabpanel"
        panel["ids"] = [f"panel-{tabs_id}-{data_tab}"]
        panel["name"] = data_tab
        panel["tabindex"] = 0
        panel["aria-labelledby"] = panel["ids"][0].replace("panel-", "tab-")
        panel["classes"].append("sphinx-tabs-panel")
        panel["classes"].extend(sorted(self.tab_classes))

        if self.env.temp_data[tabs_key]["is_first_tab"]:
            self.env.temp_data[tabs_key]["is_first_tab"] = False
        else:
            panel["hidden"] = "true"

        self.state.nested_parse(self.content[1:], self.content_offset, panel)

        if self.env.app.builder.name not in get_compatible_builders(self.env.app):
            # Use base docutils classes
            outer_node = nodes.container()
            tab = nodes.container()
            tab_name = nodes.container()
            panel = nodes.container()

            self.state.nested_parse(self.content[0:1], 0, tab_name)
            self.state.nested_parse(self.content[1:], self.content_offset, panel)

            tab += tab_name
            outer_node += tab
            outer_node += panel

            return [outer_node]

        return [panel]


def setup(app):
    app.add_directive('translatable-tab', TranslatableTabDirective)

    metadata = {'parallel_read_safe': True, 'parallel_write_safe': True}
    return metadata

