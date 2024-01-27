from typing import TYPE_CHECKING

from janim.render.renderer import Renderer

if TYPE_CHECKING:
    from janim.items.points import DotCloud


class DotCloudRenderer(Renderer):
    def init(self) -> None:
        pass

    def render(self, data: 'DotCloud.Data') -> None:
        print(self, '#' * int(abs(data.cmpt.points.get_start()[0]) + 1))
