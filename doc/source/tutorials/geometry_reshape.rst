.. _geometry_reshape:

重设几何形状
====================

有时候我们会遇到这样的情景：想要根据几何参数重新设置图形的尺寸或轮廓，我们也许会这么做：

.. code-block:: python

    # 第一次创建
    circle = Circle(radius=2)

    ...

    # ? 重设几何参数
    circle.become(Circle(radius=1.2))

虽然这种方法能够达到目的，但是这种重新创建物件的方式存在两大问题：

- 我们需要临时创建一个 :class:`~.Circle`，把它的数据“偷”过来，然后马上把它给抛弃掉，显得比较麻烦；并且这在频繁调用时会略微拖累性能
- 临时创建的 :class:`~.Circle` 无法跟随当前物件的位置，导致需要更多麻烦的操作来对齐位置

当你希望“还是同一个物件，只是换一个尺寸或轮廓”时，几何物件提供了 :meth:`~.GeometryShape.reshape` 方法来帮助你做到这一点。

``reshape`` 适合的场景
-----------------------------------------------------------------

:meth:`~.GeometryShape.reshape` 适合“参数化改形状”的需求，例如：

- 改圆的半径
- 改矩形的宽高
- 改圆角矩形的圆角大小

相比临时构造一个物件，:meth:`~.GeometryShape.reshape` 的优势是：

- 代码更简洁，直接传入新的参数即可，无需临时创建一个新物件
- 可以缺省参数，例如只改圆角矩形的圆角大小，保持宽高不变；需要另外注意的是，缺省的参数会根据原先传递给构造函数的值来决定，而不是物件当前状态的宽高
- 对于一些几何物件，可以保持当前物件的位置不变，无需额外对齐操作

使用方式
---------------

你可以把它理解为“用新的形状参数，重新描述当前物件”，可以重新设置一些原先传给构造函数的参数：

.. code-block:: python

    item.reshape(...)

在动画中，常见写法是：

.. code-block:: python

    self.play(item.anim.reshape(...))

下面用两个常见图形演示 :meth:`~.GeometryShape.reshape` 的用法。

.. janim-example:: Reshape
    :media: _static/tutorial/Reshape.mp4
    :hide_name:

    circle = Circle(radius=0.8, color=BLUE, fill_alpha=0.4).show()

    self.forward()
    self.play(circle.anim.reshape(1.8))
    self.forward(0.5)
    self.play(circle.anim.reshape(0.5))
    self.forward()

    circle.hide()

    rect = RoundedRect(3.6, 1.6, corner_radius=0.25, color=TEAL, fill_alpha=0.35).show()

    self.forward()
    self.play(rect.anim.reshape(5.2, 2.4, corner_radius=0.5))
    self.forward(0.5)
    self.play(rect.anim.reshape(corner_radius=0.15))
    self.forward(0.5)
    self.play(rect.anim.reshape(UL, DR))
    self.forward()
