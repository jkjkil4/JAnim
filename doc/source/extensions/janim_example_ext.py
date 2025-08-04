import jinja2
from docutils.parsers.rst import Directive


class JAnimExampleDirective(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    option_spec = {
        'media': str,
        'hide_name': bool,
        'hide_code': bool
    }
    final_argument_whitespace = True

    def run(self):
        scene_name = self.arguments[0]
        media_url = self.options["media"]
        hide_name = 'hide_name' in self.options
        hide_code = 'hide_code' in self.options

        if any(media_url.endswith(ext) for ext in ['.png', '.jpg', '.gif']):
            is_video = False
        else:
            is_video = True

        source_block = [
            ".. code-block:: python",
            "",
            *["    " + line for line in self.content]
        ]
        source_block = '\n'.join(source_block)

        state_machine = self.state_machine
        document = state_machine.document

        rendered_template = jinja2.Template(TEMPLATE).render(
            scene_name=scene_name,
            scene_name_lowercase=scene_name.lower(),
            media_url=media_url,
            source_block=source_block,

            is_video=is_video,
            hide_name=hide_name,
            hide_code=hide_code,
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

.. raw:: html

    </div>
'''
