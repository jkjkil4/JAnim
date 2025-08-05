基础动画
=================================

到目前为止，你已经见到了两种动画创建方式：

1. 通过 ``物件.anim`` 创建组件插值动画

2. 通过 ``动画名(物件, 动画参数)`` 为物件应用预先设置好的动画效果

.. janim-example:: BasicAnimationExample
    :media: ../_static/videos/BasicAnimationExample.mp4
    :ref: :class:`~.Create` :class:`~.SpinInFromNothing` :meth:`~.Item.anim`

    from janim.imports import *

    class BasicAnimationExample(Timeline):
        def construct(self):
            circle = Circle()
            tri = Triangle()

            self.forward()

            self.play(Create(circle))
            self.play(circle.anim.points.shift(LEFT * 3).scale(1.5))
            self.play(circle.anim.set(color=RED, fill_alpha=0.5))

            self.play(SpinInFromNothing(tri))
            self.play(tri.anim.points.shift(RIGHT * 3).scale(1.5))
            self.play(tri.anim.set(color=BLUE, fill_alpha=0.5))

            self.forward()
