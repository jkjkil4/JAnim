
from janim.gui.draw.base import Draw
from janim.gui.draw.dot import DrawDot
from janim.gui.draw.rect import DrawRect
from janim.gui.draw.vitem import DrawVItem


draw_handlers: dict[str, type[Draw]] = {
    'dot': DrawDot,
    'rect': DrawRect,
    'vitem': DrawVItem,
}
