import jinja2
from docutils.parsers.rst import Directive


class CodeDescDirective(Directive):
    has_content = True

    def run(self):
        lineno = None
        for i, line in enumerate(self.content[1:-1], start=1):
            if line == '%' and self.content[i - 1] == '' and self.content[i + 1] == '':
                lineno = i

        assert lineno is not None

        code_block = [
            ".. code-block:: python",
            "",
            *["    " + line for line in self.content[:lineno - 1]]
        ]
        code_block = '\n'.join(code_block)
        desc_block = '\n'.join(self.content[lineno + 2:])

        state_machine = self.state_machine
        document = state_machine.document

        rendered_template = jinja2.Template(TEMPLATE).render(
            code_block=code_block,
            desc_block=desc_block
        )

        state_machine.insert_input(
            rendered_template.split('\n'),
            source=document.attributes['source']
        )

        return []


def setup(app):
    app.add_directive('code-desc', CodeDescDirective)

    metadata = {'parallel_read_safe': False, 'parallel_write_safe': True}
    return metadata


TEMPLATE = '''
.. raw:: html

    <div class="janim-box">

{{ code_block }}

.. raw:: html

        <div class="janim-content">

{{ desc_block }}

.. raw:: html

        </div>
    </div>
'''
