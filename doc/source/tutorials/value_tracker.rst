ValueTracker 与自定义数据
=======================================

.. _value_tracker_basic:

基础用法
--------------------------

在 JAnim 中，可以使用 :class:`~.ValueTracker` 来变化和跟踪自定义数据的值。

例如，下面这个例子我们已经在 :ref:`item_updater_usage` 中提到过：

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

在这个例子中，我们可以注意到 :class:`~.ValueTracker` 的两个主要功能：

-   通过 :meth:`~.ValueTracker.set_value` 方法，可以设置数据的新值，并且这个变化可以通过 ``.anim`` 创建为动画

-   通过 :meth:`~.ValueTracker.get_value` 方法，可以获取数据的值

    .. important::

        在 Updater 中，需要使用 :meth:`~.Item.current` 方法来获取当前的动画状态中的 :class:`~.ValueTracker` 实例，即通过

        .. code-block:: python

            tr.current().get_value()

        来获取当前动画中的值。

        关于 :meth:`~.Item.current` 的介绍，详见 :ref:`current_usage` 。

:class:`~.ValueTracker` 不仅支持这种简单数值的变化与跟踪，还支持各种复杂结构，例如列表，字典，``numpy`` 数组等：

.. janim-example:: ComplexValueTracker
    :media: _static/tutorial/ComplexValueTracker.mp4
    :hide_name:

    tr = ValueTracker({
        'position': ORIGIN,
        'rotate': 0,
        'color': [1.0, 0.5, 0.0],
        'radius': 0.2
    })
    dots = DotCloud(
        *(
            [x, y, 0]
            for x in range(-1, 2)
            for y in range(-1, 2)
        )
    ).show()

    def dots_updater(data: DotCloud, p=None) -> None:
        value = tr.current().get_value()
        data.points.move_to(value['position']).rotate(value['rotate'])
        data.color.set(value['color'])
        data.radius.set(value['radius'])

    dots_updater(dots)

    self.forward()
    self.play(
        Succession(
            tr.anim.set_value({
                'position': UP * 1.5,
                'rotate': PI / 4,
                'color': [0.0, 0.5, 1.0],
                'radius': 0.5
            }),
            tr.anim.set_value({
                'position': LEFT * 1.5,
                'rotate': -PI / 4,
                'color': [1.0, 0.0, 0.5],
                'radius': 0.1
            }),
            tr.anim.set_value({
                'position': ORIGIN,
                'rotate': 0,
                'color': [1.0, 0.5, 0.0],
                'radius': 0.2
            }),
            tr.anim.update_value({
                'rotate': TAU,
                'color': [1.0, 1.0, 1.0]
            })
        ),
        DataUpdater(dots, dots_updater, duration=4)
    )
    self.forward()

在这个例子中，我们使用了一个包含多个字段的字典作为 :class:`~.ValueTracker` 的值，并在 Updater 中根据这些字段来更新点云的位置，旋转，颜色和半径。

相比于 :meth:`~.ValueTracker.set_value` 需要提供完整字段，我们也可以用 :meth:`~.ValueTracker.update_value` 方法来只更新部分字段的值，而不影响其他字段。

高级用法
-------------------------

除了基本的数值和结构， :class:`~.ValueTracker` 还支持沿用组件类型，以及注册自定义类型的处理。

.. note::

    说实话，高级用法的应用场景非常罕见，除非你在开发新的组件或者需要跟踪非常复杂的数据，否则大多数情况下使用基础用法就足够了。

    因此以下两个小标题 :ref:`use_component_types` 和 :ref:`register_custom_types` 的内容仅作简单介绍。

.. _use_component_types:

沿用组件类型
~~~~~~~~~~~~~~~~~~~~~~~~~

首先我们需要知道，所有 :class:`~.Component` 的子类都可以直接作为 :class:`~.ValueTracker` 的值类型，例如：

- :class:`~.Cmpt_Points`

- :class:`~.Cmpt_VPoints`

- :class:`~.Cmpt_Rgbas`

- ...

虽然说我们可以将组件类型 :class:`~.Cmpt_Points` 作为值类型直接使用，但是对于实际来讲，还是直接操作 :class:`~.Points` 物件或者含义更具体的物件，并在需要时 :meth:`~.Item.current` 会更方便。

.. _register_custom_types:

注册自定义类型
~~~~~~~~~~~~~~~~~~~~~~~~~

如果有一个类没有定义 :class:`~.SupportsTracking` 所需求的三大件 :meth:`~.Component.copy` 、 :meth:`~.Component.not_changed` 以及 :meth:`~.Component.interpolate` ，
那么我们可以通过 :meth:`~.Cmpt_Data.register_funcs` 来注册这些方法，从而让这个类可以作为 :class:`~.ValueTracker` 的值类型。具体使用方法可参考内置类型的注册。

另外，我们可以通过 :meth:`~.Cmpt_Data.register_update_func` 来注册供 :meth:`~.ValueTracker.update_value` 使用的更新方法。具体使用方法可参考内置的 ``dict`` 类型的注册。

添加自定义的物件数据
-------------------------

:class:`~.ValueTracker` 的特性完全基于 :class:`~.Cmpt_Data` 组件实现，
你完全可以将其组件添加到任意物件中，从而让你的自定义物件能够灵活地跟踪额外的数据变化，并依据你地需求灵活使用

为了添加这种组件，使用 :class:`~.CustomData` 即可，就像这样：

.. janim-example:: TestPhysicalBlock
    :media: _static/tutorial/TestPhysicalBlock.mp4
    :hide_name:

    class PhysicalBlock(Square):
        physic = CustomData()

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.physic.set({
                'speed': ORIGIN,    # 默认静止
                'accel': ORIGIN,    # 并且没有加速度
            })

        def do_physic(self, dt: float) -> Self:
            # 根据 `speed` 与 `accel` 更新物件位置
            value = self.physic.get()

            avg_speed = value['speed'] + 0.5 * value['accel'] * dt
            shift = avg_speed * dt

            self.physic.update({ 'speed': value['speed'] + value['accel'] * dt })
            self.points.shift(shift)

            return self

        def do_physic_updater(self):
            # 将 `do_physic` 包装为 Updater
            return StepUpdater(self, lambda data, p: data.do_physic(p.dt))


    class TestPhysicalBlock(Timeline):
        def construct(self):
            block = PhysicalBlock()
            block.points.to_border(DL)

            # 实时显示物块的运动向量
            def vectors_updater(p):
                cur = block.current()
                pos = cur.points.box.center
                value = cur.physic.get()

                vec_speed = Vector(value['speed'] * 0.5, color=BLUE)
                vec_speed.points.shift(pos)
                vec_accel = Vector(value['accel'] * 0.5, color=RED)
                vec_accel.points.shift(pos)

                return Group(vec_speed, vec_accel)

            self.prepare(ItemUpdater(None, vectors_updater, duration=FOREVER))

            # 物块运动以及参数变更
            self.play(block.do_physic_updater())
            block.physic.set({ 'speed': np.array([4, 6, 0]), 'accel': DOWN * 4 })
            self.play(block.do_physic_updater(), duration=2)
            block.physic.update({ 'accel': LEFT * 6 })
            self.play(block.do_physic_updater(), duration=2)

其中的 ``physic = CustomData()`` 就是我们添加的自定义数据组件，它的用法和 :class:`~.ValueTracker` 十分相似：

- 通过 :meth:`~.Cmpt_Data.set` 方法设置数据的值

- 通过 :meth:`~.Cmpt_Data.get` 方法获取数据的值

- 通过 :meth:`~.Cmpt_Data.update` 方法更新数据的部分字段

可以像这样完善其类型注解：

.. code-block:: python

    from typing import TypedDict

    class PhysicData(TypedDict):
        speed: np.ndarray
        accel: np.ndarray

    class PhysicalBlock(Square):
        physic = CustomData[Self, PhysicData]()

        ...

.. note::

    类型注解中的 ``Self`` 是为了让组件的 ``.r`` 正常运作
