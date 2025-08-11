动画系统
=================================

到目前为止，你已经见到了两种动画创建方式：

1. 通过 ``物件.anim`` 创建组件插值动画

2. 通过 ``动画名(物件, 动画参数)`` 为物件应用内置的特殊动画效果

.. janim-example:: BasicAnimationExample
    :media: ../_static/videos/BasicAnimationExample.mp4
    :hide_name:
    :ref: :class:`~.Create` :class:`~.SpinInFromNothing` :meth:`~.Item.anim`

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

基础动画参数
------------------

无论是哪种创建动画的方式，它们都有几个关键的参数

- ``duration``: 动画持续时间

  大多数动画的默认时长是 1 秒，如果你需要更长或者更短的时间可以额外设置

- ``at``: 动画开始的时间点

  意味着动画会在当前时刻的多少秒之后才开始，比如 ``at=1, duration=2`` 意味着动画会在当前时刻的 1 秒后开始，进行 2 秒

  这个参数在接下来将要讲的“动画组”的内容中，会更加实用

- ``rate_func``: 动画的缓动函数

  大多数动画默认以 :func:`~.smooth` 的方式进行插值，使得动画过程在开始和结束的时候较慢，中间过程较快，总体上表现为一个平滑的过渡

  其它一些常用的缓动函数还有 :func:`~.linear`，使得动画全程匀速进行；
  以及 :func:`~.rush_into` :func:`~.rush_from` 等，具体请参考 :ref:`rate_functions` 中的介绍

  .. image:: /_static/images/rate_functions.png

上面这些参数可以调整动画的表现细节，例如 ``duration`` 可以调整动画快慢，控制节奏， ``at`` 可以控制动画的开始时机；
当你想要让物体快速进入并逐渐减速时，可以考虑使用 :func:`~.rush_into` 作为缓动函数；总之，可以多多地探索这些参数的使用，获得更好的动画效果。

以下是对上面的动画参数进行一些调整后的示例：

.. janim-example:: BasicAnimationExampleWithParams
    :media: ../_static/tutorial/BasicAnimationExampleWithParams.mp4
    :hide_name:

    circle = Circle()
    star = Star()

    self.forward()

    self.play(Create(circle, duration=0.8, rate_func=rush_from))
    self.play(
        circle.anim(rate_func=ease_out_bounce)
            .points.shift(LEFT * 3).scale(1.5)
    )
    self.play(
        circle.anim(duration=2)
            .set(color=RED, fill_alpha=0.5)
    )

    self.play(SpinInFromNothing(star, duration=0.6, rate_func=rush_from))
    self.play(
        star.anim(rate_func=ease_out_bounce)
            .points.shift(RIGHT * 3).scale(1.5)
    )
    self.play(
        star.anim(duration=2)
            .set(color=YELLOW, fill_alpha=0.5)
    )

    self.forward()

1. 将 :class:`~.Create` 和 :class:`~.SpinInFromNothing` 的缓动函数改为了 :func:`~.rush_from`，并缩短它们进入的时长

2. 将移动动画的缓动函数改为了 :func:`~.ease_out_bounce`，使得物体在移动终点处有一个弹跳的效果

3. 将变色动画的时长改为了 2 秒

.. tip::

    在 ``.anim`` 后紧跟括号填入参数即可改变其动画参数。

    在合适的地方增加换行可以优化代码的可读性，特别是在动画调用较长的时候。

动画组
------------------

动画并不是只能像上面一样单独依次执行，我们还可以让多个动画一起执行，创建更加丰富的动画效果。

首先是最基础的， 放在同一个 ``self.play`` 函数中的动画会一起执行，你也可以给动画分别传入 ``at`` 参数来控制它们的开始时机：

.. janim-example:: GroupedAnimation
    :media: ../_static/tutorial/GroupedAnimation.mp4
    :hide_name:
    :ref: :class:`~.FadeIn` :meth:`~.Item.anim` :meth:`~.Cmpt_Points.to_border`

    circle = Circle()
    circle.points.to_border(UL, buff=LARGE_BUFF)

    square = Square()
    square.points.to_border(DL, buff=LARGE_BUFF)

    self.play(
        FadeIn(circle),
        FadeIn(square)
    )
    self.play(
        circle.anim
            .points.to_border(UR, buff=LARGE_BUFF),
        square.anim(at=0.2)
            .points.to_border(DR, buff=LARGE_BUFF)
    )

你还可以使用 :class:`~.AnimGroup` :class:`~.Succession` 等方式来组合多个动画。

- 其中 :class:`~.AnimGroup` 只是单纯地将多个动画组合到一起，可以统一应用 ``at`` 和 ``duration`` 等参数

  :class:`~.AnimGroup` 会根据传入的 ``duration`` 参数将内部动画结构进行整体伸缩以匹配时长

- :class:`~.Succession` 则会将多个动画串联起来，前一个动画结束后再开始下一个动画

.. janim-example:: ComplexGroupedAnimation
    :media: ../_static/tutorial/ComplexGroupedAnimation.mp4
    :hide_name:
    :ref: :class:`~.Succession` :class:`~.AnimGroup` :class:`~.ShowCreationThenDestructionAround`

    circle = Circle()
    circle.points.to_border(UL, buff=LARGE_BUFF)

    square = Square()
    square.points.to_border(DL, buff=LARGE_BUFF)

    self.play(
        FadeIn(circle),
        FadeIn(square)
    )
    self.play(
        Succession(
            circle.anim(rate_func=rush_into)
                .points.to_border(UR, buff=LARGE_BUFF),
            square.anim(rate_func=rush_from)
                .points.to_border(DR, buff=LARGE_BUFF),
            duration=3
        ),
        AnimGroup(
            ShowCreationThenDestructionAround(circle),
            ShowCreationThenDestructionAround(square),
            at=0.5,
            duration=2
        )
    )

.. image:: /_static/tutorial/ComplexGroupedAnimation_TimelineScreenshot.png

.. hint::

    其实 ``self.play`` 函数本身就充当一个 :class:`~.AnimGroup` 的角色，
    所以你可以直接将多个动画放在 ``self.play`` 中，并应用 ``at`` 和 ``duration`` 等参数。

.. note::

    关于动画组的更多内容，可以参考 :doc:`../janim/anims/composition` 中的介绍，
    其中还提及了关于 ``lag_ratio`` 和 ``offset`` 参数的使用，这里不再展开叙述。

预先设置动画
--------------------

当我们使用 ``self.play`` 播放一个长达 4 秒的动画之后，当前时刻便会跳转至 4 秒后，
但是我们就失去了在这 4 秒内创建其它动画的机会，因为只能往前走而不能倒退。

因此，JAnim 提供了一个实用的功能——预先设置动画，但不在时间上前进，可以调用 ``self.prepare`` 做到：

.. janim-example:: PrepareAnimation
    :media: ../_static/tutorial/PrepareAnimation.mp4
    :hide_name:
    :ref: :meth:`~.Timeline.prepare` :class:`~.Text` :class:`~.CircleIndicate`

    txt = Text('JAnim')
    txt.points.shift(LEFT * 2)

    self.prepare(
        CircleIndicate(txt),
        at=1,
        duration=2
    )

    self.play(txt.anim.points.shift(RIGHT * 4).scale(2), duration=2)
    self.play(txt.anim.points.shift(LEFT * 4).scale(0.5), duration=2)

.. image:: /_static/tutorial/PrepareAnimation_TimelineScreenshot.png

在该示例中，我们使用 ``self.prepare`` 预先设置了一个 :class:`~.CircleIndicate` 动画，
使得在文字在后续的移动动画中，能够在预先设置的时间段看到黄圈高亮的效果。

.. note::

    从原理上来讲，其实 ``play`` 就是 ``prepare + forward`` 的组合。

内置动画
------------------

关于更多可用的内置动画，可查阅以下列表中的内容：

- :doc:`../janim/anims/composition`
- :doc:`../janim/anims/creation`
- :doc:`../janim/anims/fading`
- :doc:`../janim/anims/growing`
- :doc:`../janim/anims/indication`
- :doc:`../janim/anims/movement`
- :doc:`../janim/anims/rotation`
- :doc:`../janim/anims/transform`
- :doc:`../janim/anims/updater`

JAnim 还有一个重要的特性是“动画复合”，我们将在 :ref:`updaters` 中详细介绍这一特性。

``.r`` 的使用
---------------------

在 JAnim 中，由于 **物件-组件** 的结构关系，导致在一个组件中进行完操作后，
需要使用 ``.r`` 来返回物件级别，从而再访问物件或是其它组件中的功能，例如：

.. code-block:: python

    item.points.shift(LEFT * 2).r.color.fade(0.5)

或是对于动画而言

.. code-block:: python

    self.play(
        item.anim.points.shift(LEFT * 2).r.color.fade(0.5)
    )
