.. _3d_items:

三维物件
======================

在 :ref:`3d_scene` 这一节中我们介绍了三维空间中的一些基础概念和知识，我们知道了在三维空间中，一般来说需要：

- 合适的摄像机视角

- 让物件在 ``IN`` / ``OUT`` 方向上有所移动或是在三维空间中旋转

例如上一节中我们看到的例子：

.. janim-example:: ThirdCoordShift
    :media: _static/tutorial/ThirdCoordShift.mp4
    :hide_name:
    :hide_code:

几何结构与曲面类型
-------------------------------

除了使用那些我们先前已经知道的平面几何物件让他们在三维空间中移动，JAnim 中还内置了若干的 **空间几何结构** 以及 **曲面类型**

首先我们讨论 **空间几何结构** ，举例来说，比如球体 :class:`~.Sphere` 、圆环 :class:`~.Torus` 、 圆柱 :class:`~.Cylinder` 等，
他们定义了这些三维图形的几何信息

但是，这些几何信息并不是能够直接显示在画面上的物件，我们还需要通过 :meth:`~.SurfaceGeometry.into` 将其转换为特定 **曲面类型** 的物件，包括：

- ``.into('checker')`` 得到棋盘格样式的曲面

- ``.into('vchecker')`` 也是得到棋盘格样式的曲面，但是每个面都是单独的 :class:`~.VItem`

- ``.into('wire')`` 得到线框样式的曲面

- ``.into('smooth')`` 得到平滑样式的曲面

- ``.into('dots')`` 得到点集样式的曲面

.. note::

    ``'checker'`` 类型和 ``'vchecker'`` 类型的区别在于，前者是整体渲染的棋盘格表面，后者每个面都是单独的 :class:`~.VItem` ，各有优劣：整体渲染性能更佳，而独立表面可以有更高的灵活度

比如这里演示了圆环的若干种 **曲面类型** 显示出来的样子：

.. janim-example:: TorusTypes
    :media: _static/tutorial/TorusTypes.png
    :hide_name:

    shape = Torus(1, 0.5)
    torus1 = shape.into('checker')
    torus2 = shape.into('wire')
    torus3 = shape.into('smooth')
    torus4 = shape.into('dots')

    group = Group(torus1, torus2, torus3, torus4).show()
    group.points.arrange_in_grid()
    self.camera.points.set(orientation=quat(0.36, -0.04, -0.11, 0.93))
    self.camera.points.shift([0, -0.3, -0.32])

以及一个更完整的演示：

.. janim-example:: ThreeDShapesExample
    :extract-from-example-mark:
    :media: _static/videos/ThreeDShapesExample.mp4
    :ref: :meth:`~.SurfaceGeometry.into` :meth:`~.BuiltTimeline.to_item` :class:`~.RectClip`

自定义几何结构
-----------------------------

.. note::

    文档有待完善

自定义曲面类型
-----------------------------

.. note::

    文档有待完善
