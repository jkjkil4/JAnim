from janim.items.item import Item
from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.typing import Vect


class Points(Item):
    '''
    点集

    纯数据物件，不参与渲染
    '''
    points = CmptInfo(Cmpt_Points)

    def __init__(self, *points: Vect, **kwargs):
        super().__init__(**kwargs)

        self.points.set(points)
