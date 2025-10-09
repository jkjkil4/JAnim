详解深度
==============================

基础知识
-----------------

JAnim 的深度机制控制了物件的绘制顺序，深度越大的物件，会被深度越低的物件遮挡：

.. janim-example:: Depth1
    :media: _static/tutorial/Depth1.png
    :hide_name:

    txt = Text('Example Text', font_size=40).show()
    circle = Circle(color=BLUE, fill_alpha=1, depth=1).show()

在上面这个示例中，我们将圆的深度设置为 1，而文字的深度默认为 0，因此圆会被文字遮挡。

如果两个物件具有相同的深度，它们的遮挡关系遵循 **“越早创建的物件，越会被遮挡”** 即 **“更迟创建的物件，显示在其它物件的前面”** 的原则：

.. janim-example:: Depth2
    :media: _static/tutorial/Depth2.png
    :hide_name:

    txt = Text('Example Text', font_size=40).show()
    circle = Circle(color=BLUE, fill_alpha=1).show()

在上面这个示例中，文字和圆的深度都是 0，但是文字会被圆遮挡，因为文字先创建，而圆后创建。

重新设置深度
-------------------

对于同深度的物件，在有需要的情况下，你可以重新设置其深度，以更新它们的遮挡关系：

.. janim-example:: Depth3
    :media: _static/tutorial/Depth3.png
    :hide_name:

    txt = Text('Example Text', font_size=40).show()
    circle = Circle(color=BLUE, fill_alpha=1).show()

    txt.depth.set(0)

这样，文字的深度虽然一开始是 0，但是我们通过 ``txt.depth.set(0)`` 将其深度再次设置为 0，更新了深度设置的先后顺序，这样文字又重新出现在了圆的前面。

.. note::

    所以，上文提到的 **“更迟创建的物件，显示在其它物件的前面”** 的本质其实是：

    .. raw:: html

        <div align="center">

    **“更迟设置深度的物件，显示在其它物件的前面”**

    .. raw:: html

        </div>

    当然，这句话只是深度相同时遵循的原则。

.. tip::

    在上面这个示例中，完全可以将 ``txt.depth.set(0)`` 换成 ``txt.depth.arrange()``，
    因为 :meth:`~.Cmpt_Depth.arrange` 在不指定深度时，就会将当前带有的深度值传入 :meth:`~.Cmpt_Depth.set` 进行调用，
    起到与 ``txt.depth.set(0)`` 一样的效果。

深度的排列
-------------------

将多个物件放到一个 :class:`~.Group` 中时，并不会改变它们原有的深度，例如对于

.. code-block::

    star = Star(fill_alpha=1, outer_radius=1.5, color=YELLOW).show()
    star.points.shift(UL)

    circle = Circle(fill_alpha=1, color=BLUE).show()
    circle.points.shift(UR)

    square = Square(fill_alpha=1, color=PURPLE).show()

我们显然可以知道，圆会显示在星星的前面，并且方形还会显示在圆的前面。

哪怕把他们都放到一个 :class:`~.Group` 中，也不会按照在 :class:`~.Group` 中出现的顺序来调整深度，仍然保持原有的深度：

.. janim-example:: GroupDepth1
    :media: _static/tutorial/GroupDepth1.png
    :hide_name:

    star = Star(fill_alpha=1, outer_radius=1.5, color=YELLOW).show()
    star.points.shift(UL)

    circle = Circle(fill_alpha=1, color=BLUE).show()
    circle.points.shift(UR)

    square = Square(fill_alpha=1, color=PURPLE).show()

    group = Group(square, circle, star)

上面这个例子中，我们故意把 ``star`` ``circle`` ``square`` 倒过来放到 ``group`` 中，确实仍然是星星在最后面，方形在最前面。

但是，如果我们此时对 ``group`` 使用 :meth:`~.Cmpt_Depth.arrange` 方法，或者在其构造时传入 ``depth`` 参数，则会按照 ``group`` 的深度重新设置：

.. janim-example:: GroupDepth2
    :media: _static/tutorial/GroupDepth2.png
    :hide_name:

    star = Star(fill_alpha=1, outer_radius=1.5, color=YELLOW).show()
    star.points.shift(UL)

    circle = Circle(fill_alpha=1, color=BLUE).show()
    circle.points.shift(UR)

    square = Square(fill_alpha=1, color=PURPLE).show()

    group = Group(square, circle, star)
    group.depth.arrange()

可以看到，在执行了 :meth:`~.Cmpt_Depth.arrange` 后，方形就到了最后面，而星星出现在了最前面。

渲染顺序的原理
----------------

.. include:: /rst_utils/tip_of_complex.rst

对于不同深度值的物件，它们的渲染顺序非常浅显易懂，只需按照深度的大小排列即可。

于是这里主要讨论相同深度值的物件，是怎么做到“更迟设置深度的物件，显示在其它物件的前面”的。

其实，深度信息不止 ``.set(...)`` 所传入的值，他还暗藏一个“序号”，越后面设置的物件，它的“序号”就越低，
所以，对于相同深度值的物件，JAnim 判定渲染顺序的方法便是使用“序号”作为依据。

物件深度“序号”的具体值可以使用 :meth:`~.Cmpt_Depth.get_raw` 获取，这是一个包含两个值的 ``tuple``，分别是 ``(depth, order)``：

.. janim-example:: DepthRawDisplay
    :media: _static/tutorial/DepthRawDisplay.png
    :hide_name:

    txt = Text('Example Text', font_size=120).show()

    for ch in txt[0]:
        num = Text(f'{ch.depth.get_raw()}', font_size=12).show()
        num.points.next_to(ch.get_mark_orig(), DR, buff=0.05)

.. warning::

    在同一次的程序执行过程中，哪怕重新构建时间轴，或是导出动画，物件深度的计数不会重置，因此在上面这个示例中，显示值在每次重新构建时间轴后都会进一步递减。

    因此在创建动画过程时，动画效果绝对不要依赖于物件深度“序号”的具体值，否则会影响效果的一致性。
