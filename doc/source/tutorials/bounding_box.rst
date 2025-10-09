.. _bounding_box:

边界框
=============

简要介绍
---------------

边界框是几何物件的一个重要概念。具体来说，边界框是一个外接矩形，反映了物件的坐标范围。

以下是各种常见几何图形的外接矩形，即边界框区域：

.. janim-example:: BoundingBoxForCommonShapes
    :media: _static/tutorial/BoundingBoxForCommonShapes.png
    :hide_name:
    :hide_code:

可以看出，背景的红色包围矩形正好把几何图形框在里面，矩形的四条边恰好覆盖到图形的最左、最右、最上、最下方。

.. hint::

    只有未旋转的矩形与其边界框完全重合

边界框正是 JAnim 用来处理上一节中 :ref:`relative_placement` 的方式 —— 他们本质上是以物件的边界框为依据进行对齐和放置的。

获取关键坐标
----------------

如果你想获取边界框上的几个特殊点的位置，例如边界框的左侧中心点，右侧中心点等，以单位圆为例：

.. janim-example:: BoundingBoxPoints
    :media: _static/tutorial/BoundingBoxPoints.png
    :hide_name:

    circle = Circle().show()

    print(circle.points.box.left)       # [-1.0, 0.0, 0.0]
    print(circle.points.box.top)        # [0.0, 1.0, 0.0]
    print(circle.points.box.get(DR))    # [1.0, -1.0, 0.0]

可以发现，边界框的所有信息，都可以通过 ``.points.box`` 获取；
如果你有大量访问边界框信息的需求，甚至可以先将 ``.points.box`` 赋值给一个变量，然后再使用这个变量来获取边界框的相关信息：

.. code-block:: python

    circle = Circle().show()
    box = circle.points.box

    print(box.left, box.top, box.get(DR))
    # [-1.0, 0.0, 0.0] [0.0, 1.0, 0.0] [1.0, -1.0, 0.0]

    circle.points.shift(RIGHT)
    new_box = circle.points.box

    print(box.left, box.top, box.get(DR))
    # [-1.0, 0.0, 0.0] [0.0, 1.0, 0.0] [1.0, -1.0, 0.0]

    print(new_box.left, new_box.top, new_box.get(DR))
    # [0.0, 0.0, 0.0] [1.0, 1.0, 0.0] [2.0, -1.0, 0.0]

.. hint::

    在物件移动后，原先赋值的 ``box`` 变量仍保留原有的信息

除了使用以上方式获取边界框四周的点之外，还可以通过 ``.points.box.center`` 得到边界框的中心点

.. janim-example:: BoundingBoxCenterForCommonShapes
    :media: _static/tutorial/BoundingBoxCenterForCommonShapes.png
    :hide_name:
    :hide_code:

其实，边界框的中心点正是 :meth:`~.Cmpt_Points.move_to` 等函数的参考位置：当你使用 ``move_to`` 尝试将物件移动至某个位置时，JAnim 所做的就是将物件移动，使其边界框中心点到达你所指定的位置。

边界框的局限性
----------------------------

边界框对物件几何特征的刻画足以应对大多数情况下的需求，但是当我们讨论“几何中心”时，边界框中心时常与形状的“几何中心”不重合。

你可能注意到了上图中用淡绿色标记的点，这就是他们的几何中心：
只有圆和方形的边界框中心与几何中心重合，其余图形的边界框中心则偏离了几何中心。

这些几何图形的几何中心，也就是淡绿色的点，在 JAnim 中被打上了额外的标记，你可以通过 ``.mark.get()`` 来获取，例如：

.. janim-example:: TwoCenterOfTriangle
    :media: _static/tutorial/TwoCenterOfTriangle.png
    :hide_name:

    tri = Triangle(radius=3).show()

    Dot(tri.points.box.center, color=BLUE).show()
    Dot(tri.mark.get(), color=GREEN).show()

对于有关内容，可参考 :class:`~.MarkedItem` 与 :class:`~.Cmpt_Mark`
