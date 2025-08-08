物件组
==============

可以使用 :class:`~.Group` 将多个物件组合在一起，这样便可以依照整体的边界框进行整体位移、排列和对齐，以及设置属性与应用动画。

物件组的常用方法
---------------------

以下给出了两个示例及其解析：

.. janim-example:: GroupExample1
    :media: ../_static/tutorial/GroupExample1.mp4
    :hide_name:
    :ref: :class:`~.Group` :meth:`~.Cmpt_Points.arrange` :meth:`~.Cmpt_Rgbas.fade`

    group = Group(
        Star(), Circle(), RegularPolygon(6),
        color=BLUE,
        fill_alpha=1
    )
    group.points.arrange(RIGHT, buff=MED_LARGE_BUFF)

    self.play(FadeIn(group))
    self.play(group(VItem).anim.fill.fade(0.7))
    self.play(Rotate(group, TAU), duration=3)
    self.play(FadeOut(group, lag_ratio=0.5))

.. code-desc::

    group = Group(
        Star(), Circle(), RegularPolygon(6),
        color=BLUE,
        fill_alpha=1
    )
    group.points.arrange(RIGHT, buff=MED_LARGE_BUFF)

    %

    这里创建了一个 ``group``，其中包含了三个子物件： ``Star`` 、 ``Circle`` 和 ``RegularPolygon``，并将它们统一设置为蓝色且完全填充。

    并通过 :meth:`~.Cmpt_Points.arrange` 方法，将 ``group`` 中的子物件依次向右排列，前后间距为 ``MED_LARGE_BUFF``。

    .. hint::

        :meth:`~.Cmpt_Points.arrange` 是 JAnim 中排列物件的一个相当实用的方法，
        还有 :meth:`~.Cmpt_Points.arrange_in_grid` 方法提供了网格排列的功能，
        可另行参考阅读。

.. code-desc::

    self.play(group(VItem).anim.fill.fade(0.7))

    %

    将填充颜色整体淡化 70%。

    由于 :class:`~.Group` 没有像几何图形物件 :class:`~.VItem` 一样的复杂属性，因此不能直接使用类似 ``group.fill.fade(0.7)`` 这样的方式来淡化颜色。

    但是可以通过 ``group.astype(VItem).fill.fade(0.7)`` 的方式，把 ``group`` “当作”一个 :class:`~.VItem` 来使用原本没有的组件，可以简写为

    .. code-block:: python

        group(VItem).fill.fade(0.7)

    形式上来讲，写法是： ``group(当作什么物件).组件.操作``。

    因为这里是用作动画，所以形式上是 ``group(当作什么物件).anim.组件.操作``。

.. code-desc::

    self.play(FadeOut(group, lag_ratio=0.5))

    %

    :class:`~.FadeOut` 动画的 ``lag_ratio`` 参数可以控制子物件淡出的延迟比率，
    默认 ``0`` 表示同时淡出，这里设置了 ``0.5`` 表示前一个淡出 50% 后开始淡出下一个。

.. janim-example:: GroupExample2
    :media: ../_static/tutorial/GroupExample2.mp4
    :hide_name:
    :ref: :class:`~.Group` :meth:`~.Cmpt_Points.arrange` :class:`~.Indicate`

    group = Group(
        Star(color=GOLD, fill_alpha=0.5),
        Circle(color=RED),
        RegularPolygon(6, color=BLUE, fill_alpha=0.5),
    )
    group.points.arrange(RIGHT, buff=MED_LARGE_BUFF)

    self.play(FadeIn(group))

    self.play(Indicate(group))
    for sub in group:
        self.play(Indicate(sub))

    self.play(group[1].anim.fill.set(alpha=0.5))

    self.play(FadeOut(group, lag_ratio=0.5))

.. code-desc::

    group = Group(
        Star(color=GOLD, fill_alpha=0.5),
        Circle(color=RED),
        RegularPolygon(6, color=BLUE, fill_alpha=0.5),
    )

    %

    这里创建了一个 ``group``，其中包含了三个子物件，每个子物件初始化了不同的颜色。

.. code-desc::

    self.play(Indicate(group))
    for sub in group:
        self.play(Indicate(sub))

    %

    首先用 :class:`~.Indicate` 动画高亮显示整个 ``group``

    并且我们可以使用 ``for`` 遍历组内的子物件，依次使用 :class:`~.Indicate` 动画高亮它们。

.. code-desc::

    self.play(group[1].anim.fill.set(alpha=0.5))

    %

    通过 ``group[1]`` 访问 ``group`` 中下标为 1 的，即第二个子物件 ``Circle``，将其填充透明度设置为 ``0.5``。

物件组的嵌套
---------------------

显而易见，我们完全可以把一个 :class:`~.Group` 作为另一个 :class:`~.Group` 的子物件（这里笔者随便搓了一个 ``HelloJAnimExample`` 代码的示意动画）：

.. janim-example:: NestedGroupExample
    :media: ../_static/tutorial/NestedGroupExample.mp4
    :hide_name:
    :ref: :class:`~.Text` :class:`~.Group` :class:`~.Arrow` :class:`~.Transform`

    txt = Text('self.play(Transform(circle, square))')

    shapes = Group(
        Circle(color=BLUE),
        Arrow(color=YELLOW),
        Square(color=GREEN, fill_alpha=0.5)
    )
    shapes.points.scale(0.5).arrange(RIGHT, buff=MED_LARGE_BUFF)

    group = Group(txt, shapes)
    group.points.arrange(DOWN, aligned_edge=LEFT)

    self.play(Write(group))
    self.forward(0.5)
    self.play(
        FadeOut(txt),
        FadeOut(shapes[1:]),
        shapes[0].anim.points.scale(2).to_center()
    )
    self.play(
        Transform(shapes[0], Square(color=GREEN, fill_alpha=0.5))
    )

这里将一个“圆形指向方形”的 ``shapes`` 组对齐到文字的下方，然后又和文字创建了一个 ``group`` 组。

在进行动画时，通过对各元素的操作以及对物件组的切片（例如 ``shapes[1:]``）来创建各种动画效果。

有关物件组的用法你可以继续挖掘，探索更多可能！

.. note::

    其实文字物件就是一个嵌套的物件组，其中包含了多个“文字行”物件，每个“文字行”物件又包含多个“字符”物件。

    具体可参阅 :doc:`../janim/items/text` 文档中的介绍。