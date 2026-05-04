.. _camera_usage:

摄像机的使用
=====================

基础知识
---------------------

我们知道，一个基本的 JAnim 时间轴长这样：

.. code-block:: python

    class MyTimeline(Timeline):
        def construct(self):
            ...

JAnim 中内置了一个摄像机物件，我们可以通过 ``self.camera`` 访问

摄像机物件像普通物件一样平移、旋转以及缩放：

.. janim-example:: CameraZoomIn
    :media: _static/tutorial/CameraZoomIn.mp4
    :hide_name:

    # 螺线参数方程
    def t_func(self, t):
        scale = 0.01
        return np.array([
            scale * np.cos(t) * t**2,
            scale * np.sin(t) * t**2,
            0,
        ])

    # 坐标系
    plane = NumberPlane(faded_line_ratio=1)
    # 创建螺线
    curve = ParametricCurve(t_func, t_range=[0, 5 * TAU, 0.2], color=YELLOW)

    self.show(plane, curve)

    self.forward()
    self.play(
        self.camera.anim.points.rotate(PI / 2).scale(0.25), # 旋转并缩放相机
        curve.anim.radius.scale(0.25),  # 缩放螺线粗细
        duration=3
    )
    self.forward()

.. janim-example:: MovingCamera
    :media: _static/tutorial/MovingCamera.mp4
    :hide_name:

    # 坐标系
    axes = Axes(axis_config={ 'include_numbers': True })
    # 创建正方形
    square = Square()
    square.points.shift(UR * 2)

    self.show(axes, square)

    self.forward()
    self.play(
        self.camera.anim.points.shift(LEFT * 2),
        self.camera.anim(duration=2).points.move_to(square),
        Wait(0.5),
        self.camera.anim(duration=1.5).points.to_center(),
        lag_ratio=1
    )
    self.forward()

需要注意的是，摄像机缩放在 <1 的时候是放大画面，在 >1 的时候是缩小画面

这是因为我们缩放的是摄像机的大小而不是画面的大小，缩小摄像机，缩小了“取景范围”，画面自然就会被放大，反之亦然

将物件固定在摄像机画面中
-------------------------------------

移动摄像机会改变视野范围，让画面整体移动

而有些时候，我们会想让某些物件仍保持在画面中不动，比如标题文本或是一些提示文本等

为了达到这个目的，我们可以使用 :meth:`~.Item.fix_in_frame` 方法来做到，比如我们稍微修改一下上面的例子得到：

.. janim-example:: MovingCameraWithFixedItems
    :media: _static/tutorial/MovingCameraWithFixedItems.mp4
    :hide_name:

    # 坐标系
    axes = Axes(axis_config={ 'include_numbers': True })
    # 创建正方形
    square = Square()
    square.points.shift(UR * 2)

    # 摄像机中心点以及文字
    dot = Dot(ORIGIN, color=BLUE).fix_in_frame()
    txt1 = Text('Camera Center', color=BLUE).fix_in_frame()
    txt1.points.next_to(dot, DOWN)

    # 画面左上角文字
    txt2 = Text('Moving the camera ...').fix_in_frame()
    txt2.points.to_border(UL)

    self.show(axes, square, dot, txt1, txt2)

    self.forward()
    self.play(
        self.camera.anim.points.shift(LEFT * 2),
        self.camera.anim(duration=2).points.move_to(square),
        Wait(0.5),
        self.camera.anim(duration=1.5).points.to_center(),
        lag_ratio=1
    )
    self.forward()

在这个例子中，我们让一个 ``dot`` 表示摄像机中心，并通过 :meth:`~.Item.fix_in_frame` 达到了 ``dot`` 以及若干提示文本在画面中保持不动的效果

配合动画方法动态调整位置
------------------------------------

和一般的物件一样，显然我们也可以用一些动画来控制摄像机的位置，来达到一些有意思的效果：

.. janim-example:: CameraOnCurve
    :media: _static/tutorial/CameraOnCurve.mp4
    :hide_name:

    axes = Axes(
        (0, 10), (0, 5),
        axis_config={
            'include_tip': True,
            'include_numbers': True,
        }
    )
    graph = axes.get_graph(lambda x: math.sin(x) + x / 2, color=BLUE)

    dot = SmallDot(axes.c2p(), glow_alpha=0.5)

    self.show(axes, graph)
    self.camera.points.move_to(axes)
    self.camera.save_state()

    self.play(
        self.camera.anim.points.move_to(dot).scale(0.35),
        FadeIn(dot, scale=0.5),
    )
    self.play(
        MoveAlongPath(dot, graph),
        MoveAlongPath(self.camera, graph),
        duration=4
    )
    self.play(
        FadeOut(dot),
        self.camera.anim.load_state()
    )

同样的，你也可以给摄像机加上一些 Updater，可以另行尝试一下。

其它
--------------------

JAnim GUI 提供了一个方便的功能在预览窗口调整摄像机，可另行参阅 :ref:`guicmd_camera` 进行了解

对于在三维空间中使用摄像机，另行参考 :ref:`3d_scene` 页面中的介绍

