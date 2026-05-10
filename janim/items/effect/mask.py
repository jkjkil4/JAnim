from typing import Self
from janim.components.component import CmptInfo
from janim.components.simple import Cmpt_Alpha, Cmpt_Float
from janim.components.vpoints import Cmpt_VPoints
from janim.items.effect.frame_effect import AppliedGroup
from janim.items.item import Item
from janim.items.vitem import VItem
from janim.render.renderer_shapemask import ShapeMaskRenderer


class ShapeMask(AppliedGroup):
    """
    以 ``shape`` 为轮廓做一个蒙板效果

    对于传入的物件，只会显示形状内部的部分

    :param shape: 蒙板图形，若带有后代物件，则将若干后代物件图形作 XOR

        若要使用后代物件的并，可参考 :meth:`~.boolean_ops.Union.from_group`，例如

        .. code-block:: python

            ShapeMask(..., shape=boolean_ops.Union.from_group(shape))

    :param alpha: 蒙板整体透明度，范围 ``0.0 ~ 1.0``
    :param feather: 边缘羽化大小，值越大越模糊；数值上体现为羽化部分的两侧的距离
    :param invert: 反转蒙板， ``0.0`` 为正常， ``1.0`` 为完全反转

    .. code-block:: python

        text = Text('Hello').show()
        mask = ShapeMask(text, shape=Circle(radius=2), feather=0.2)
        mask.show()

    嵌套蒙板和 :class:`~.FrameEffect` 一样，需要显式嵌套 :class:`~.ShapeMask` 对象：

    .. code-block:: python

        mask1 = ShapeMask(..., shape=shape1).show()
        mask2 = ShapeMask(mask1, shape=shape2).show()
    """

    renderer_cls = ShapeMaskRenderer

    points = CmptInfo(Cmpt_VPoints[Self])

    alpha = CmptInfo(Cmpt_Alpha[Self], 1.0)
    feather = CmptInfo(Cmpt_Float[Self], 0.0)
    invert = CmptInfo(Cmpt_Float[Self], 0.0)

    def __init__(
        self,
        *items,
        shape: Item,
        alpha: float = 1.0,
        feather: float = 0.0,
        invert: bool = False,
        root_only: bool = False,
        **kwargs,
    ):
        super().__init__(
            *items,
            root_only=root_only,
            **kwargs,
        )

        subpaths = []
        for item in shape.walk_self_and_descendants():
            if isinstance(item, VItem):
                subpaths.extend(item.points.get_subpaths())

        for subpath in subpaths:
            self.points.add_subpath(subpath)

        self.alpha.set(alpha)
        self.feather.set(feather)
        self.invert.set(invert)
