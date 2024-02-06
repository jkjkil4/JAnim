from janim.components.component import CmptInfo, CmptGroup
from janim.components.vpoints import Cmpt_VPoints
from janim.components.rgbas import Cmpt_Rgbas
from janim.components.radius import Cmpt_Radius
from janim.items.points import Points
from janim.render.impl import VItemRenderer


class VItem(Points):
    points = CmptInfo(Cmpt_VPoints)
    radius = CmptInfo(Cmpt_Radius)

    stroke = CmptInfo(Cmpt_Rgbas)
    fill = CmptInfo(Cmpt_Rgbas)

    color = CmptGroup(stroke, fill)

    renderer_cls = VItemRenderer
