坐标系统
==========

JAnim 的坐标系统不以像素为单位，而是采用水平方向约 ``-7.11 ~ 7.11``，垂直方向 ``-4 ~ 4`` 的坐标范围，形成一个 16:9 的画面。

原点位于画面中心，向右向上为正方向，下图展现了创建在 JAnim 画面上的坐标系网格以及放置于原点处的单位圆：

.. janim-example:: CoordinatesGrid
    :media: _static/tutorial/CoordinatesGrid.png
    :hide_name:

    NumberPlane(faded_line_ratio=0).show()

    circle = Circle(color=YELLOW).show()

.. hint::

    这里的 ``xxx.show()`` 与 ``self.show(xxx)`` 一样，都是将物件直接显示出来

.. note::

    为了方便起见，这里提供的代码省略了 ``construct`` 方法之外的内容，只展示 ``construct`` 的核心部分

    类似情况不再赘述

在之前的简要介绍中，我们提到 JAnim 的几何 **物件** 含有多个 **组件**，包括 ``points``、 ``stroke``、 ``fill`` 等；
而其中与坐标系统相关的组件是 ``points``，它决定了物件的形状和位置。

所以在大多数情况下，当我们想要“操作物件的坐标”时，先 ``.points`` 再做具体操作就对了！

坐标平移
-------------

``points`` 组件提供了多种方法来操作物件的坐标，这里先介绍两个基础方法：

.. list-table::

    *   - 方法
        - 示例
        - 描述

    *   - :meth:`~.Cmpt_Points.shift`
        - ``.shift(RIGHT * 3 + UP * 2)``
        - 根据给定的位移平移物件

    *   - :meth:`~.Cmpt_Points.move_to`
        - ``.move_to(ORIGIN)``
        - 将物件移动到指定位置

例如，使用 ``.move_to(RIGHT * 3 + UP * 2)`` 可以将物件移动到坐标系中 ``(3,2)`` 的位置：

.. janim-example:: MoveTo
    :media: _static/tutorial/MoveTo.png
    :hide_name:

    circle = Circle(color=YELLOW).show()
    circle.points.move_to(RIGHT * 3 + UP * 2)

上面的例子中，我们组合 ``UP`` （向上） 和 ``RIGHT`` （向右） 这两个内置向量表示出了圆的位移；
你也可以猜到，还有 ``DOWN`` （向下） 和 ``LEFT`` （向左） 这两个内置向量可以使用。

这些内置向量方便在 JAnim 中快速表示坐标位移，只需要使用位移距离乘以方向，再依次组合即可。

JAnim 还内置了更多额外方向，如图所示：

.. janim-example:: BuiltinDirections
    :media: _static/tutorial/BuiltinDirections.png
    :hide_name:
    :hide_code:

.. hint::

    边上的这四个向量需要使用 ``Config.get`` 来获取，这是因为他们是由视框大小这一可配置项所决定的，
    并不是像单位向量这样的固定向量。

    关于 :class:`~.Config` 的更多内容，可以参考 :ref:`config_system`。

除了使用内置方向的组合表示坐标，还可以直接使用坐标值来表示位置。

例如，上面提到的 ``.move_to(RIGHT * 3 + UP * 2)`` 等效于 ``.move_to([3, 2, 0])``，也就是将物件移动到 ``[3, 2, 0]`` 的位置。

.. important::

    尽管我们现在讨论的是画面上的二维坐标，但其实 JAnim 的坐标系统是三维的，物件和摄像机可以在空间中自由移动，所以这里还出现了第三个分量。

    但在大多数情况下，我们只需要关注前两个坐标轴（x 和 y）就够用了，将 z 轴取为 0 即可。

    关于三维坐标的更多内容，可以参考 :ref:`3d_coordinates`。

.. _relative_placement:

相对放置
----------------

除了上述的平移方法，物件还可以放置在其它物件以及边界旁边：

.. list-table::

    *   - 方法
        - 示例
        - 描述

    *   - :meth:`~.Cmpt_Points.next_to`
        - ``.next_to(square, RIGHT)``
        - 将物件放置在另一个物件旁边

    *   - :meth:`~.Cmpt_Points.align_to`
        - ``.align_to(square, UP)``
        - 将物件与另一个物件在某个方向上对齐

    *   - :meth:`~.Cmpt_Points.to_border`
        - ``.to_border(UL)``
        - 将物件放到画面某个方向的边界旁

让我们结合动画来演示这些方法的使用，这里是将一个圆形四处移动，尝试放在矩形旁边以及边界旁边：

.. tip::

    回忆一下，对于立刻作用的 ``circle.points.next_to(...)`` 等方法，
    在物件后面插入 ``.anim`` 便可使其成为可播放的动画，即

    .. code-block:: python

        circle.anim.points.next_to(...)

.. janim-example:: RelativePlacement
    :media: _static/tutorial/RelativePlacement_SpeedDown.mp4
    :hide_name:

    square = Square().show()
    square.points.move_to([-3, -1, 0])

    circle = Circle(radius=0.5, color=YELLOW)

    self.play(Create(circle))

    self.play(circle.anim.points.next_to(square, RIGHT))
    self.play(circle.anim.points.next_to(square, RIGHT, buff=MED_LARGE_BUFF))
    self.play(circle.anim.points.next_to(square, RIGHT, buff=MED_LARGE_BUFF, aligned_edge=UP))

    self.forward()

    self.play(circle.anim.points.to_border(UP))
    self.play(circle.anim.points.to_border(UR))
    self.play(circle.anim.points.to_border(UR, buff=LARGE_BUFF))
    self.play(circle.anim.points.to_border(UL))

    self.forward()

    self.play(circle.anim.points.align_to(square, UP))
    self.play(circle.anim.points.to_border(UL))
    self.play(circle.anim.points.align_to(square, LEFT))

    self.forward()

.. note::

    上面提供的动画代码实际执行时没有坐标系网格和文字备注，那些是笔者额外添加的；

    且进行了降速处理，方便观看动画过程。

示例中的方法出现了一些额外的参数：

- ``buff``

  表示物件与目标物件或边界之间的间距，间距从小到大可用 ``SMALL_BUFF``、 ``MED_SMALL_BUFF``、 ``MED_LARGE_BUFF``、 ``LARGE_BUFF`` 以及直接数值表示

  物件之间的间距默认为 ``MED_SMALL_BUFF``，物件与边界直接的间距默认为 ``MED_LARGE_BUFF``。

- ``aligned_edge``

  表示物件与目标物件的对齐边缘，

  比如示例中的 ``aligned_edge=UP`` 表示将圆形放置在方形右侧的同时，使它们的上边缘对齐。

形状变换
-----------------

常用的形状变换包括缩放与旋转：

.. list-table::

    *   - 方法
        - 示例
        - 描述

    *   - :meth:`~.Cmpt_Points.scale`
        - ``.scale(2)``
        - 缩放物件

    *   - :meth:`~.Cmpt_Points.stretch`
        - ``.stretch(2, dim=0)``
        - 在某个方向上拉伸物件，``dim=0 dim=1 dim=2`` 分别表示 x、y、z 轴

    *   - :meth:`~.Cmpt_Points.rotate`
        - ``.rotate(PI / 4)``
        - 旋转物件，逆时针为正方向

让我们结合动画来演示这些方法的使用，这里是将一个正六边形进行若干形状变换：

.. janim-example:: ShapeTransformation
    :media: _static/tutorial/ShapeTransformation_SpeedDown.mp4
    :hide_name:

    poly = RegularPolygon(6).show()

    self.forward()
    self.play(poly.anim.points.scale(2))
    self.play(poly.anim.points.rotate(PI / 6))
    self.play(poly.anim.points.stretch(2, dim=0))
    self.play(poly.anim.points.scale(0.25, about_edge=RIGHT))
    self.play(poly.anim.points.rotate(120 * DEGREES, about_point=ORIGIN))
    self.play(Rotate(poly, 120 * DEGREES, about_point=ORIGIN))
    self.play(poly.anim.points.rotate(PI / 2))
    self.forward()

首先对于旋转操作，传入的数值应是弧度制，JAnim 也内置了常用角度的常量，如 ``PI`` 和 ``TAU``。
也可以使用如 ``30 * DEGREES`` 的形式表示角度值，这与 ``PI / 6`` 等价。

对于一些额外的参数：

- ``about_edge``

  表示缩放或旋转时的参考边缘，默认为 ``ORIGIN``，即物件的中心点。

  例如在 ``.scale(0.25, about_edge=RIGHT)`` 中，将缩放的参考点设置为物件的右边缘，使得物件被缩小时右边缘位置不变，其余部分向右边缘聚拢。

- ``about_point``

  表示缩放或旋转时的参考点，默认为 ``None``，会根据 ``about_edge`` 取参考点，即默认以物件的中心；

  可以设置为某个点，表示以全局坐标中的该点为参考点。

  例如在 ``.rotate(120 * DEGREES, about_point=ORIGIN)`` 中，将旋转的参考点设置为全局坐标的原点，使得物件围绕原点旋转。

.. code-desc::

    self.play(poly.anim.points.rotate(120 * DEGREES, about_point=ORIGIN))
    self.play(Rotate(poly, 120 * DEGREES, about_point=ORIGIN))

    %

    这两行看起来都是“将物件绕原点逆时针旋转 120 度”，但其实存在本质上的差异。

    前者是 ``poly`` 的组件动画，本质上是对操作前后的 ``poly`` 的 **插值效果**，是直线变换而非弧线移动，并没有真正的旋转效果；

    而后者 :class:`~.Rotate` 作为专门的一个动画类，使得物件沿着圆弧路径旋转，产生真正的旋转效果。

    另请参考 :ref:`janim_anims_rotation` 页面的介绍。
