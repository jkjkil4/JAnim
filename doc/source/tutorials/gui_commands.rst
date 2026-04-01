GUI 命令
===================

GUI 命令允许在 :meth:`~.Timeline.construct` 方法中使用 ``self('命令内容')`` 的形式在 GUI 中打开功能交互面板。

更为重要的是，面板的交互结果在提交后，可以 **应用到源代码上**。

GUI 命令的基本用法是：

.. code-block:: python

    self('命令名称: 命令参数')

.. important::

    命令必须使用完整的字符串字面量，不能使用变量或表达式传递命令名称和参数。

    正是有了这样的限制，JAnim 才能将 GUI 中的操作正确地修改到源代码中。

.. note::

    文档有待完善，目前这里的内容较为简略

``select`` 命令
-----------------------

选择指定物件的子物件

尝试：

.. code-block:: python

    typ = TypstText('#lorem(4)', scale=3).show()

    self('select: typ').set(color=RED)
    self('select: typ').set(color=GREEN)
    self('select: typ').set(color=BLUE)

.. code-block:: python

    txt = Text('This is the first line.\nThis is the second line.').show()

    self('select: txt[0]').set(color=RED)
    self('select: txt[1]').set(color=GREEN)

``camera`` 命令
------------------------

自由转动/移动/缩放摄像机视角

尝试：

.. code-block:: python

    ThreeDAxes(
        axis_config={
            'include_tip': True
        }
    ).show()

    circle = Circle().show()
    circle.points.rotate(40 * DEGREES, axis=UP)

    self('camera')

.. code-block:: python

    NumberPlane(faded_line_ratio=1).show()

    square1 = Square(color=RED, fill_alpha=1)
    square2 = Square(color=GREEN, fill_alpha=1)
    square3 = Square(color=BLUE, fill_alpha=1)

    square2.points.rotate(PI / 2, axis=UP)
    square3.points.rotate(PI / 2, axis=RIGHT)

    squares = Group(square1, square2, square3)
    squares.show().apply_depth_test()

    self('camera')

``move`` 命令
-------------------------

移动物件的位置，支持自动吸附

尝试：

.. code-block:: python

    circle = Circle().show()
    square = Square().show()
    rect = Rect(6, 0.5).show()

    self('move: circle, square, rect')
