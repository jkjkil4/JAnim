.. _updaters:

Updater 的使用
=====================

``Updater`` 系列的动画类是 JAnim 中一套强大的功能，包括：

- :class:`~.DataUpdater` 以及 :class:`~.GroupUpdater`

- :class:`~.StepUpdater` 以及 :class:`~.GroupStepUpdater`

- :class:`~.ItemUpdater`

我们将逐一介绍，并介绍若干重要的特性。

学懂 Updater 后，你就可以从基础教程“毕业”了！

.. warning::

    JAnim 中的 ``Updater`` 系列动画类与 Manim 中的 ``updater`` 在概念上存在较大差异，若套用 Manim 中的概念可能导致理解偏差。

概述
-----------------

使用内置的动画时，我们只能播放一种特定的的动画效果，而使用 Updater，我们可以使用代码更灵活地使控制物件每一帧的状态。

为了理解这些 Updater 之间的区别，我们现在需要将讨论的核心聚焦在 **动画是基于什么状态创建的** ：

- :class:`~.DataUpdater` 和 :class:`~.GroupUpdater` 基于 **“起始时刻的状态”**

- :class:`~.StepUpdater` 和 :class:`~.GroupStepUpdater` 基于 **“上一帧的状态”**

- :class:`~.ItemUpdater` 很特殊，它不基于任何状态

你可能暂时对以上的描述感到陌生，我们接下来将会进一步地介绍它们，你不必担心。

不过你目前可以从以上的描述中看出，:class:`~.DataUpdater` 和 :class:`~.GroupUpdater` 是一类的，而 :class:`~.StepUpdater` 和 :class:`~.GroupStepUpdater` 是一类的。

这样，你就可以从理解 5 种 Updater，简化到理解 3 种 Updater，这就是我们接下来的话题。

使用 DataUpdater 与 GroupUpdater
-------------------------------------------------------

我们先从介绍 :class:`~.DataUpdater` 开始，它是最基础也是应用范围最广的一种 Updater，许多 JAnim 内置的动画都基于它实现。

它的作用是基于起始时刻的状态，以时间为参数对物件进行修改：

.. janim-example:: BasicDataUpdater
    :media: _static/tutorial/BasicDataUpdater.mp4
    :hide_name:

    square = Square()

    self.play(
        DataUpdater(
            square,
            lambda data, p: data.points.rotate(p.alpha * PI)
        ),
        duration=3
    )

我们在前面提到，Updater 最核心的功能就是“通过代码控制物件每一帧的状态”，这里的 ``data.points.rotate(p.alpha * PI)`` 就是我们控制物件的代码，起到了让正方形顶点逆时针旋转的效果。

我们需要了解 ``lambda data, p: data.points.rotate(p.alpha * PI)`` 表示了什么含义，是如何让物件旋转起来的：

- 其中的 ``data`` 和 ``p`` 分别表示 **“物件初始状态”** 以及 **“当前的时间信息”** ，这两个是 JAnim 提供的

- 冒号 ``:`` 后面就是我们需要完成的部分，这里我们使用 ``data.points.rotate(p.alpha * PI)`` 表示 “以初始状态为基础，旋转 ``p.alpha * PI`` 度”

.. note::

    这里的 ``p.alpha`` 表示的是动画进度，会随着动画的进行，从 0 逐渐增长到 1；常用的属性还包括：

    - ``p.global_t`` 表示当前的全局时刻

    - ``p.elapsed`` 表示到当前时可动画持续了多久，这是对 ``p.global_t - p.at`` 的简写 

我们完整地解读这个代码，即为：

.. raw:: html

   <strong>

正方形从初始状态 ``data`` 开始，根据动画的进度 ``p.alpha`` 旋转

.. raw:: html

   </strong>

动画向前推进地越多，旋转量越大，这样就起到了逐渐旋转的效果。

.. hint::

    其实上面这个示例正是内置的 :class:`~.Rotate` 和 :class:`~.Rotating` 动画的实现方式

-----

在设计上，:class:`~.DataUpdater` 只是为了修改单个物件自身的状态而使用的，
哪怕你给他传入 ``root_only=False`` 参数，也只是给所有后代物件逐个采用相同的效果，而不是将他们作为一个整体来操作。

而如果我们需要将一个物件组作为整体进行这样的动画，就需要用到 :class:`~.GroupUpdater` 了：

.. janim-example:: BasicGroupUpdater
    :media: _static/tutorial/BasicGroupUpdater.mp4
    :hide_name:

    squares = Square() * 2  # 与 squares = Group(Square(), Square()) 基本等价
    squares.points.arrange()

    self.play(
        GroupUpdater(
            squares,
            lambda group, p: group.points.rotate(p.alpha * PI)
        ),
        duration=3
    )

可以发现，:class:`~.GroupUpdater` 的使用与 :class:`~.DataUpdater` 基本一致，区别只在于我们将 ``squares`` 作为一个整体进行旋转。

.. warning::

    原则上来说，传入 :class:`~.DataUpdater` 以及 :class:`~.GroupUpdater` 等 ``Updater`` 的函数不应产生“副作用”，也就是只能改变 ``data`` 的状态，应避免产生对函数之外其它变量的影响。

-----

最后我们附上一个 ``root_only=False`` 的 :class:`~.DataUpdater` 与 :class:`~.GroupUpdater` 的对比。

.. raw:: html

    <div class="detail-box">
    <details>
    <summary>

点击展开

.. raw:: html

    </summary>

前者是对各个后代物件独立应用旋转效果，后者是作为一个整体应用旋转效果。

.. janim-example:: DataUpdaterVsGroupUpdater
    :media: _static/tutorial/DataUpdaterVsGroupUpdater.mp4
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

.. raw:: html

    </details>
    </div>

有关 Updater 的一些实用操作
---------------------------------------------

我们刚介绍完 :class:`~.DataUpdater` 与 :class:`~.GroupUpdater` ，在介绍剩下的 Updater 之前，我们先了解一些有关 Updater 的实用操作。

.. _current_usage:

``current()`` 的功能
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

对于传入 ``Updater`` 的函数而言，在动画过程中如果需要访问 **其它正在进行动画的物件** 的当前状态，可以在对应物件后面加上 ``.current()`` 来获取。

.. warning::

    如果不加 :meth:`~.Item.current`，只会得到 ``construct`` 函数中对应物件的最终状态，而非动画过程中的状态。

.. janim-example:: ArrowPointingExample
    :extract-from-example:
    :no-construct:
    :media: _static/videos/ArrowPointingExample.mp4

.. hint::

    ``dot2.update.points.rotate(TAU, about_point=RIGHT * 2)`` 相当于

    .. code-block:: python

        GroupUpdater(
            dot2,
            lambda group, p: group.points.rotate(TAU * p.alpha, about_point=RIGHT * 2)
        )

    这是一种简化写法，但并不是所有方法都可以这样简化，你可以具体试一试。

在这个示例中，我们首先将 ``dot2`` 围绕一个圆周进行运动。

然后在 ``arrow`` 的 ``Updater`` 函数中，
使用 ``.current()`` 便可以得到 ``dot2`` 当前运动到的位置，从而让箭头始终指向 ``dot2`` 。

动画复合
~~~~~~~~~~~~~~~~~~~~~

JAnim 的各个 ``Updater`` 并非孤立，不仅可以使用 ``.current()`` 获知其它物件的当前动画状态，还可以在一个物件上 **叠加多个** ``Updater``，依次应用动画效果。

在下面这个例子中，我们每两秒加入一个新的 ``Updater``，以演示“动画复合”的作用：

.. janim-example:: CombineUpdatersExample
    :extract-from-example:
    :no-construct:
    :media: _static/videos/CombineUpdatersExample.mp4

.. tip::

    可以给 ``Updater`` 传入 ``become_at_end=False`` 使物件在动画后回到最初的状态。

    但是 ``.anim`` 没有这种参数，所以这里每次都有 ``square.points.to_border(LEFT)``。

.. warning::

    ``.anim`` 所创建的动画具有覆盖性，当其参与“动画复合”时，应将其放在最开始使用。

这里另外再给出一个“动画复合”的示例：

.. janim-example:: RotatingPieExample
    :extract-from-example:
    :no-construct:
    :media: _static/videos/RotatingPieExample.mp4
    :ref: :class:`~.Sector` :func:`~.rotate_vector`

``duration=FOREVER`` 的功能
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

我们可以使用 ``duration=FOREVER`` 来创建一个持续进行的 ``Updater`` ，例如：

.. janim-example:: ForeverUpdater
    :media: _static/tutorial/ForeverUpdater.mp4
    :hide_name:

    square = Square().show()

    self.forward()

    self.prepare(
        DataUpdater(
            square,
            lambda data, p: data.points.rotate(p.elapsed * 60 * DEGREES),
            duration=FOREVER
        )
    )

    self.prepare(
        DataUpdater(
            square,
            lambda data, p: data.points.set_x(2 * math.sin(p.alpha * TAU)),
            become_at_end=False
        ),
        at=2,
    )

    self.forward(5)

使用 StepUpdater 与 GroupStepUpdater
---------------------------------------------------

:class:`~.StepUpdater` 与 :class:`~.GroupStepUpdater` 的关系就像是 :class:`~.DataUpdater` 与 :class:`~.GroupUpdater` 之间的关系 
—— 一个是对一个物件自身进行操作，另一个是将整个物件组作为一个整体来操作。

我们先介绍一下 :class:`~.StepUpdater` ，它的作用是按步更新物件，适合用于 **“需要基于上一刻的状态更新下一刻状态”** 的情景，例如物理模拟或是微分方程数值演示等。

.. note::

    我们将 :class:`~.StepUpdater` 的每一次状态更新称之为“一步”，且在构造时使用 ``step`` 参数表示每秒钟包含多少次更新，并不与帧率相关

以下是一个最简单（但也是最没必要使用 :class:`~.StepUpdater` ）的一个示例：

.. janim-example:: SimplestStepUpdater
    :media: _static/tutorial/SimplestStepUpdater.mp4
    :hide_name:

    NumberPlane(faded_line_ratio=1).show()

    circle = Circle(0.5, color=YELLOW, fill_alpha=0.6).show()

    self.forward()
    self.play(
        StepUpdater(
            circle,
            lambda data, p: data.points.shift(RIGHT / 50)
        ),
        duration=2
    )
    self.forward()

在这个示例中，:class:`~.StepUpdater` 的函数会每次将圆形向右移动 1/50 个单位，
由于 :class:`~.StepUpdater` 默认情况下每秒钟会执行 50 次，经过两秒则时间则总共向右移动了 2 个单位。

.. note::

    如果你有使用 Manim 的经验，其 ``updater`` 会与 :class:`~.StepUpdater` 的这套逻辑更为相似

下面是一个更复杂的例子，
我们结合 :class:`~.CustomData` 给物件附加了“速度”与“加速度”这两个物理属性，
在这个例子中演示了物件依赖这些属性的动态变化

.. raw:: html

    <div class="detail-box">
    <details>
    <summary>

点击展开

.. raw:: html

    </summary>

.. janim-example:: UpdatingPhysicalBlock
    :extract-from-test-mark:
    :media: _static/tutorial/UpdatingPhysicalBlock.mp4
    :hide_name:

关于 :class:`~.CustomData` 以及这个例子的具体介绍，可以参考教程页面 :ref:`add_custom_data` ，这里暂时略过。

.. raw:: html

    </details>
    </div>

-----

关于与 :class:`~.StepUpdater` 一套的 :class:`~.GroupStepUpdater` ，功能上是一致的，区别仅为是否将物件组看作一个整体来处理，方便处理大量小球碰撞等场景：

.. janim-example:: BallsCollisionExample
    :media: _static/tutorial/BallsCollisionExample.mp4
    

    class Ball(Dot):
        speed = CustomData()

        def __init__(self, radius: float):
            super().__init__(radius=radius, color=BLUE)
            self.speed.set(ORIGIN)


    class BallsCollisionExample(Timeline):
        def construct(self):
            # 有关配置
            left = -4
            right = 4
            bottom = -3
            top = 3

            radius = 0.25
            ball_count = 25

            # 容器边框
            Polygon([left, top, 0], [left, bottom, 0], [right, bottom, 0], [right, top, 0], fill_alpha=0.2).show()
            # 内部的球
            balls = Ball(radius) * ball_count

            # 生成互不重叠的初始位置
            positions = []
            rng = np.random.default_rng(1234)
            for ball in balls:
                # 初始位置
                ...

                # 初始速度
                ...

            def updater(group: Group[Ball], p) -> None:
                dt = p.dt

                # 1. 根据速度移动
                for ball in group:
                    ball.points.shift(ball.speed.get() * dt)

                # 2. 与容器边界碰撞
                ...

                # 3. 小球之间的完全弹性碰撞
                ...

            self.play(
                GroupStepUpdater(balls, updater),
                duration=4,
            )

            ball_follow = balls[6]

            self.forward(0.5)
            self.play(
                self.camera.anim.points.scale(0.5).move_to(ball_follow),
                ball_follow.anim.set(color=YELLOW),
            )
            self.forward(0.5)
            self.play(
                GroupStepUpdater(balls, updater),
                Follow(self.camera, ball_follow, ORIGIN),
                duration=6,
            )

.. raw:: html

    <div class="detail-box">
    <details>
    <summary>

点击查看完整代码

.. raw:: html

    </summary>

.. code-block:: python

    class Ball(Dot):
        speed = CustomData()

        def __init__(self, radius: float):
            super().__init__(radius=radius, color=BLUE)
            self.speed.set(ORIGIN)


    class BallsCollisionExample(Timeline):
        def construct(self):
            # 有关配置
            left = -4
            right = 4
            bottom = -3
            top = 3

            radius = 0.25
            ball_count = 25

            # 容器边框
            Polygon([left, top, 0], [left, bottom, 0], [right, bottom, 0], [right, top, 0], fill_alpha=0.2).show()
            # 内部的球
            balls = Ball(radius) * ball_count

            # 生成互不重叠的初始位置
            positions = []
            rng = np.random.default_rng(1234)
            for ball in balls:
                # 初始位置
                while True:
                    pos = np.array([
                        rng.uniform(left + radius, right - radius),
                        rng.uniform(bottom + radius, top - radius),
                        0,
                    ])
                    if all(np.linalg.norm(pos - other) >= 2 * radius for other in positions):
                        break
                ball.points.move_to(pos)
                positions.append(pos)

                # 初始速度
                ball.speed.set(
                    np.array([
                        rng.uniform(-3, 3),
                        rng.uniform(-3, 3),
                        0,
                    ])
                )

            def updater(group: Group[Ball], p) -> None:
                dt = p.dt

                # 1. 根据速度移动
                for ball in group:
                    ball.points.shift(ball.speed.get() * dt)

                # 2. 与容器边界碰撞
                for ball in group:
                    pos = ball.points.box.center
                    speed = ball.speed.get().copy()

                    if pos[0] - radius < left:
                        ball.points.set_x(left + radius)
                        speed[0] = abs(speed[0])

                    elif pos[0] + radius > right:
                        ball.points.set_x(right - radius)
                        speed[0] = -abs(speed[0])

                    if pos[1] - radius < bottom:
                        ball.points.set_y(bottom + radius)
                        speed[1] = abs(speed[1])

                    elif pos[1] + radius > top:
                        ball.points.set_y(top - radius)
                        speed[1] = -abs(speed[1])

                    ball.speed.set(speed)

                # 3. 小球之间的完全弹性碰撞
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        ball1 = group[i]
                        ball2 = group[j]

                        p1 = ball1.points.box.center
                        p2 = ball2.points.box.center

                        delta = p2 - p1
                        dist = np.linalg.norm(delta)

                        min_dist = 2 * radius

                        if dist >= min_dist:
                            continue

                        # 两个球存在重合时，给出碰撞方向
                        if dist < 1e-8:
                            normal = np.array([1.0, 0.0, 0.0])
                            dist = 0.0
                        else:
                            normal = delta / dist

                        v1 = ball1.speed.get()
                        v2 = ball2.speed.get()

                        # 相对速度
                        relative_velocity = v2 - v1
                        velocity_along_normal = np.dot(relative_velocity, normal)
                        # 只有相互靠近时才处理碰撞
                        if velocity_along_normal < 0:
                            # 相同质量的完全弹性碰撞
                            impulse = velocity_along_normal * normal
                            ball1.speed.set(v1 + impulse)
                            ball2.speed.set(v2 - impulse)

                        # 消除两个球之间的重叠
                        overlap = min_dist - dist
                        if overlap > 0:
                            correction = normal * (overlap / 2)
                            ball1.points.shift(-correction)
                            ball2.points.shift(correction)

            self.play(
                GroupStepUpdater(balls, updater),
                duration=4,
            )

            ball_follow = balls[6]

            self.forward(0.5)
            self.play(
                self.camera.anim.points.scale(0.5).move_to(ball_follow),
                ball_follow.anim.set(color=YELLOW),
            )
            self.forward(0.5)
            self.play(
                GroupStepUpdater(balls, updater),
                Follow(self.camera, ball_follow, ORIGIN),
                duration=6,
            )

.. raw:: html

    </details>
    </div>

关于 :class:`~.CustomData` 的具体介绍，可以参考教程页面 :ref:`add_custom_data` 。

.. _item_updater_usage:

使用 ItemUpdater
------------------------------------------

:class:`~.ItemUpdater` 和前面介绍的两种 ``Updater`` 存在很大的差异，传入前面两个 ``Updater`` 的函数都会收到两个参数 ``data, p`` 或是 ``group, p`` ，
但是 :class:`~.ItemUpdater` 只会提供一个参数 ``p`` ，并且 **将函数返回的物件直接渲染到画面上** 。

:class:`~.ItemUpdater` 的使用场景是在动画过程中动态创建物件以显示，例如数值持续变化的文字：

.. janim-example:: DynamicNumber
    :media: _static/tutorial/DynamicNumber.mp4
    :hide_name:

    tr = ValueTracker(0)
    txt = Text('0.00', font_size=40).show()

    self.forward()
    self.play(
        Succession(
            tr.anim.set_value(4),
            tr.anim.set_value(2.5),
            tr.anim.set_value(10)
        ),
        ItemUpdater(
            txt,
            lambda p: Text(f'{tr.current().get_value():.2f}', font_size=40),
            duration=3
        )
    )
    self.forward()

.. janim-example:: UpdaterExample
    :extract-from-example:
    :no-construct:
    :media: _static/videos/UpdaterExample.mp4
    :ref: :class:`~.Brace`

.. note::

    从原理上来讲，由于 :class:`~.ItemUpdater` 不依赖任何状态，仅用于显示函数所返回的物件，
    因此传入 :class:`~.ItemUpdater` 的第一个参数的物件与动画过程其实没有任何关系。

    :class:`~.ItemUpdater` 所干的，在默认情况下其实就是：

    - 在动画开始时，把传入的物件隐藏
    - 在动画过程中，渲染函数所返回的物件
    - 在动画结束后，把传入的物件显示，并调用 :meth:`~.Item.become` 方法将传入物件改变成动画最后一刻的样子

    所以 :class:`~.ItemUpdater` 可以不传入物件，传入 ``None`` 也是可以的。
