.. _updaters:

Updater 的使用
=====================

``Updater`` 系列的动画类是 JAnim 中一套强大的功能，包括 :class:`~.DataUpdater` :class:`~.GroupUpdater` :class:`~.ItemUpdater` :class:`~.StepUpdater`，
我们将逐一介绍，并介绍若干重要的特性。

学懂 :class:`~.DataUpdater` :class:`~.GroupUpdater` 以及 :class:`~.ItemUpdater` 后，你就可以从基础教程“毕业”了！

.. warning::

    JAnim 中的 ``Updater`` 系列动画类与 Manim 中的 ``updater`` 在概念上存在较大差异，若套用 Manim 中的概念可能导致理解偏差。

``DataUpdater`` 的使用
--------------------------------------------------------

:class:`~.DataUpdater` 是最基础也是应用范围最广的一种 ``Updater``，它的作用是以时间为参数对物件进行修改：

.. janim-example:: BasicDataUpdater
    :media: ../_static/tutorial/BasicDataUpdater.mp4
    :hide_name:

    square = Square()

    self.play(
        DataUpdater(
            square,
            lambda data, p: data.points.rotate(p.alpha * PI)
        ),
        duration=3
    )

在这里，我们给 :class:`~.DataUpdater` 传入了一个函数，这个函数的作用是：将正方形的顶点进行旋转，以产生动画效果。

那么这个函数是如何起作用的呢？形式上来说，:class:`~.DataUpdater` 的格式是：

.. code-block:: python

    DataUpdater(物件, lambda 物件初始状态, 时间信息: <根据时间信息改变初始状态>)

.. tip::

    你可以根据需要选择使用 ``lambda`` 函数还是 ``def`` 函数，这取决于具体的使用情景。

    在功能简单的情况下，使用 ``lambda`` 函数会更加方便。

其中时间信息有 ``p.alpha`` 表示当前动画的进度， ``p.global_t`` 表示当前的全局时刻等。

所以，对于 ``lambda data, p: data.points.rotate(p.alpha * PI)`` 而言，这个函数的作用是：

**将正方形从动画的初始状态，根据动画的进度进行旋转，动画向前推进得越多，那么旋转量就会越大**

从而产生矩形物件旋转的动画效果。

.. note::

    其实上面这个示例正是 :class:`~.Rotate` 和 :class:`~.Rotating` 动画的实现方式

.. hint::

    你可以使用 ``p.global_t - p.t_range.at`` 得知，到当前时刻动画持续了多久。

需要注意的是，如果传递给 :class:`~.DataUpdater` 的物件有子物件，
在默认情况下 ``root_only=True`` 只对根物件自身进行操作，
若传入 ``root_only=False``，则会对其所有后代物件都分别应用 ``Updater`` 的效果，但并不会将他们作为一个整体进行操作。

为了将物件及其后代物件作为一个整体进行操作，我们就需要引出 :class:`~.GroupUpdater`，我们马上在下一个小节介绍。

.. warning::

    原则上来说，传入 :class:`~.DataUpdater` 以及 :class:`~.GroupUpdater` 等 ``Updater`` 的函数不应产生“副作用”，也就是只能改变 ``data`` 的状态，应避免产生对函数之外其它变量的影响。

``GroupUpdater`` 的使用
--------------------------------------------------------

:class:`~.GroupUpdater` 在用法上和 :class:`~.DataUpdater` 一致，都是以时间为参数对物件进行修改。

但正如在上一小节对 :class:`~.DataUpdater` 的介绍中提到的，:class:`~.GroupUpdater` 侧重于将传入物件及其后代物件作为一个整体操作，
这在处理如“整体旋转”和“整体对齐”等操作时比较实用。

以下示例展示了使用 :class:`~.DataUpdater` 和 :class:`~.GroupUpdater` 进行旋转的区别：

.. janim-example:: DataUpdaterVsGroupUpdater
    :media: ../_static/tutorial/DataUpdaterVsGroupUpdater.mp4
    :hide_name:

    squares1 = Square() * 2
    squares1.points.arrange()

    squares2 = squares1.copy()

    group = Group(
        Text('DataUpdater'), Text('GroupUpdater'),
        squares1, squares2
    ).show()
    group.points.arrange_in_grid(buff=LARGE_BUFF)

    self.play(
        DataUpdater(
            squares1,
            lambda data, p: data.points.rotate(p.alpha * PI),
            root_only=False
        ),
        GroupUpdater(
            squares2,
            lambda data, p: data.points.rotate(p.alpha * PI)
        ),
        duration=4
    )

.. tip::

    在能得到相同效果（如平移而非旋转）时，
    :class:`~.DataUpdater` 的性能会优于 :class:`~.GroupUpdater`。

``current()`` 的使用
-----------------------------------

对于传入 ``Updater`` 的函数而言，在动画过程中如果需要访问 **其它正在进行动画的物件** 的当前状态，可以在对应物件后面加上 ``.current()`` 来获取。

.. warning::

    如果不加 :meth:`~.Item.current`，只会得到 ``construct`` 函数中对应物件的最终状态，而非动画过程中的状态。

.. janim-example:: ArrowPointingExample
    :media: ../_static/videos/ArrowPointingExample.mp4
    :hide_name:

    dot1 = Dot(LEFT * 3)
    dot2 = Dot()

    arrow = Arrow(dot1, dot2, color=YELLOW)

    self.show(dot1, dot2, arrow)
    self.play(
        dot2.update.points.rotate(TAU, about_point=RIGHT * 2),
        GroupUpdater(
            arrow,
            lambda data, p:
                data.points.set_start_and_end(
                    dot1.points.box.center,
                    dot2.current().points.box.center
                ).r.place_tip()
        ),
        duration=4
    )

.. hint::

    ``dot2.update.points.rotate(TAU, about_point=RIGHT * 2)`` 相当于

    .. code-block:: python

        DataUpdater(
            dot2,
            lambda data, p: data.points.rotate(TAU * p.alpha, about_point=RIGHT * 2)
        )

    这是一种简化写法，但并不是所有方法都可以这样简化。

在这个示例中，我们首先将 ``dot2`` 围绕一个圆周进行运动。

然后在 ``arrow`` 的 ``Updater`` 函数中，
使用 ``.current()`` 便可以得到 ``dot2`` 当前运动到的位置，从而让箭头始终指向 ``dot2``。

动画复合
---------------------

JAnim 的各个 ``Updater`` 并非孤立，不仅可以使用 ``.current()`` 获知其它物件的当前动画状态，还可以在一个物件上 **叠加多个** ``Updater``，依次应用动画效果。

在下面这个例子中，我们每两秒加入一个新的 ``Updater``，以演示“动画复合”的作用：

.. janim-example:: CombineUpdatersExample
    :media: ../_static/videos/CombineUpdatersExample.mp4

    square = Square()
    square.points.to_border(LEFT)

    self.play(
        square.anim.points.to_border(RIGHT),
        duration=2
    )

    ###############################

    square.points.to_border(LEFT)
    self.play(
        square.anim.points.to_border(RIGHT),
        DataUpdater(
            square,
            lambda data, p: data.points.shift(UP * math.sin(p.alpha * 4 * PI)),
            become_at_end=False
        ),
        duration=2
    )

    ###############################

    square.points.to_border(LEFT)
    self.play(
        square.anim.points.to_border(RIGHT),
        DataUpdater(
            square,
            lambda data, p: data.points.shift(UP * math.sin(p.alpha * 4 * PI)),
            become_at_end=False
        ),
        square.update(become_at_end=False).color.set(BLUE).r.points.rotate(-TAU),
        duration=2
    )

.. tip::

    可以给 ``Updater`` 传入 ``become_at_end=False`` 使物件在动画后回到最初的状态。

    但是 ``.anim`` 没有这种参数，所以这里每次都有 ``square.points.to_border(LEFT)``。

.. warning::

    ``.anim`` 所创建的动画具有覆盖性，当其参与“动画复合”时，应将其放在最开始使用。

这里另外再给出一个“动画复合”的示例：

.. janim-example:: RotatingPieExample
    :media: ../_static/videos/RotatingPieExample.mp4
    :hide_name:
    :ref: :class:`~.Sector` :func:`~.rotate_vector`

    pie = Group(*[
        Sector(start_angle=i * TAU / 4, angle=TAU / 4, radius=1.5, color=color, fill_alpha=1, stroke_alpha=0)
            .points.shift(rotate_vector(UR * 0.05, i * TAU / 4))
            .r
        for i, color in enumerate([RED, PURPLE, MAROON, GOLD])
    ])

    self.play(
        GroupUpdater(
            pie,
            lambda data, p: data.points.rotate(p.alpha * TAU, about_point=ORIGIN),
            duration=5
        ),
        DataUpdater(
            pie[0],
            lambda data, p: data.points.shift(normalize(data.mark.get()) * p.alpha),
            rate_func=there_and_back,
            become_at_end=False,
            at=2,
            duration=2
        )
    )

``ItemUpdater`` 的使用
------------------------------------------

:class:`~.ItemUpdater` 和前面介绍的两个 ``Updater`` 存在很大的差异，传入前面两个 ``Updater`` 的函数都会收到两个参数 ``data, p``，
但是 :class:`~.ItemUpdater` 只会提供一个参数 ``p``，并且 **将函数返回的物件直接渲染到画面上**。

:class:`~.ItemUpdater` 的使用场景是在动画过程中动态创建物件以显示，例如数值持续变化的文字：

.. janim-example:: DynamicNumber
    :media: ../_static/tutorial/DynamicNumber.mp4
    :hide_name:

    v = ValueTracker(0)
    txt = Text('0.00', font_size=40).show()

    self.forward()
    self.play(
        Succession(
            v.anim.data.set(4),
            v.anim.data.set(2.5),
            v.anim.data.set(10)
        ),
        ItemUpdater(
            txt,
            lambda p: Text(f'{v.current().data.get():.2f}', font_size=40),
            duration=3
        )
    )
    self.forward()

.. janim-example:: UpdaterExample
    :media: ../_static/videos/UpdaterExample.mp4
    :ref: :class:`~.Brace`

    square = Square(fill_color=BLUE_E, fill_alpha=1).show()
    brace = Brace(square, UP).show()

    def text_updater(p: UpdaterParams):
        cmpt = brace.current().points
        return cmpt.create_text(f'Width = {cmpt.brace_length:.2f}')

    self.prepare(
        DataUpdater(
            brace,
            lambda data, p: data.points.match(square.current())
        ),
        ItemUpdater(None, text_updater),
        duration=10
    )
    self.forward()
    self.play(square.anim.points.scale(2))
    self.play(square.anim.points.scale(0.5))
    self.play(square.anim.points.set_width(5, stretch=True))

    w0 = square.points.box.width

    self.play(
        DataUpdater(
            square,
            lambda data, p: data.points.set_width(
                w0 + 0.5 * w0 * math.sin(p.alpha * p.range.duration)
            )
        ),
        duration=5
    )
    self.forward()

.. note::

    从原理上来讲，传入 :class:`~.ItemUpdater` 的物件与动画过程其实没有任何关系。

    :class:`~.ItemUpdater` 所干的，在默认情况下其实就是：

    - 在动画开始时，把传入的物件隐藏
    - 在动画过程中，渲染函数所返回的物件
    - 在动画结束后，把传入的物件显示，并调用 :meth:`~.Item.become` 方法将传入物件改变成动画最后一刻的样子

    所以 :class:`~.ItemUpdater` 可以不传入物件，传入 ``None`` 也是可以的。

``StepUpdater`` 的使用
------------------------------------

按步更新物件

.. note::

    文档有待完善
