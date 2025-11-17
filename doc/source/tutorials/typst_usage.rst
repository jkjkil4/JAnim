.. _typst_usage:

Typst 的使用
======================

简要介绍
---------------------

如果你是从 Manim 迁移过来的用户，你可能对 LaTeX 有一定的了解。

当我们在 JAnim 中使用 Typst，就像是在 Manim 中使用 LaTeX，可以通过代码的形式创建排版或公式。

我们常用 :class:`~.TypstText` 和 :class:`~.TypstMath` 来在 JAnim 中使用 Typst

.. code-block:: python

    typ1 = TypstText(R'This is a #text(aqua)[sentence] with a math expression $cos^2 x + sin^2 x = 1$')
    typ2 = TypstMath(R'cos^2 theta + sin^2 theta = 1')

.. tip::

    当你使用了 VS Code 插件 ``janim-toolbox``，出现在 ``TypstText`` 中的 **Raw-字符串** （类似 ``R'...'`` 的形式）会作为 Typst 代码高亮颜色，如下图所示

    .. image:: /_static/tutorial/TypstHighlight.png

    较为遗憾的是，在 :class:`~.TypstMath` 中的 Raw-字符串 暂时没有该功能。

如果你更倾向于使用 JAnim 展示公式，那么你更可能会经常用到 :class:`~.TypstMath`。

Typst 物件的类型
--------------------------

Typst 物件分为三种：

- :class:`~.TypstText` 表示 Typst 文字，传入的字符串不会被 ``$ $`` 所包裹

- :class:`~.TypstMath` 表示 Typst 公式，传入的字符串会被包裹在 ``$ $`` 中作为公式进行编译

- :class:`~.TypstDoc` 是所有其它 Typst 物件的基类，它表示一个 Typst 文档

  :class:`~.TypstDoc` 与 :class:`~.TypstText` 和 :class:`~.TypstMath` 不同，它会自动与画面的最上方对齐，有一种“从文档的开头开始查看”的感觉

也就是说，:class:`~.TypstText` 和 :class:`~.TypstMath` 的区别仅是是否被包裹在公式环境中，例如 ``TypstMath('x^2')`` 和 ``TypstText('$ x^2 $')`` 在大多数情况下是等效的

Typst 子物件索引
------------------------

基础用法
~~~~~~~~~~~~~~~~~~~~~~

对于普通的物件，使用 :ref:`subitem_selector` 比较方便；而对于 Typst 物件，有更加方便的索引方式： **字符索引**

比如对于 :class:`~.TypstMath` 对象

.. code-block:: python

  typ = TypstMath('cos^2 theta + sin^2 theta = 1')

可以使用 ``typ['cos']`` 得到 ``cos`` 对应的部分，这样你就可以使用类似于 ``typ['cos'].set(color=BLUE)`` 的方式进行着色，或进行其它处理。

当出现多个匹配时的处理
~~~~~~~~~~~~~~~~~~~~~~~~~~

你应该注意到了这里有两个“θ”（``theta``），当你使用 ``typ['theta']`` 的方式进行索引时，将会取出第一个匹配的 θ，也就是前一个。

因为他们是从 ``0``、 ``1``、... 依次编号的，所以在这个例子中你可以使用 ``typ['theta', 1]`` 得到后一个。

.. note::

   这也意味着 ``t['theta']`` 和 ``t['theta', 0]`` 是等效的

.. janim-example:: TypstColorizeExample
    :media: _static/videos/TypstColorizeExample.mp4

    typ = TypstMath('cos^2 theta + sin^2 theta = 1', scale=3).show()

    self.forward()
    self.play(typ['cos'].anim.set(color=BLUE))
    self.play(typ['sin'].anim.set(color=BLUE))
    self.play(typ['theta', 0].anim.set(color=GOLD))
    self.play(typ['theta', 1].anim.set(color=ORANGE))
    self.forward()
    self.play(typ['theta', ...].anim.set(color=GREEN))
    self.play(typ['space^2', ...].anim.set(color=RED))
    self.forward()

如果想要同时取出多个，则将多个编号写在一个序列中即可，例如 ``typ['theta', (0, 1)]`` 则是取出编号为 ``0`` 和 ``1`` 的匹配项，在这里就是所有匹配到的 θ 符号。

你应该发现了，取出 ``(0, 1)`` 的项，其实就是取出所有项，对于这种情况，JAnim 提供了 ``typ['theta', ...]`` 的方式，使用省略号表示取出所有的匹配项。

一些特殊情况
~~~~~~~~~~~~~~~~~~~~~~~~~~

当你想要取出

.. code-block:: python

  typ = TypstMath('cos^2 theta + sin^2 theta = 1')

中的上标 “2” 时，使用 ``typ['2']`` 无法匹配到它，这是因为上标的 “2” 和普通的 “2” 长得不同。

为了正确匹配，你需要把索引中的 2 也表示为“上标”的形式，例如 ``typ['""^2']`` 或者 ``typ['space^2']``，
这两者都是把 “2” 作为一个空元素（ ``""`` 或者 ``space`` ） 的上标，这样就可以正确匹配了。

.. important::

    上面以 :class:`~.TypstMath` 作为字符索引的例子，:class:`~.TypstDoc` 和 :class:`~.TypstText` 也是几乎一致的，但是会有略微区别

    我们知道，在这三种对象中，只有 :class:`~.TypstMath` 是在公式环境中的，所以进行它的字符索引时，作为索引的字符串也会在公式环境中解析

    这意味着，对于 :class:`~.TypstDoc` 和 :class:`~.TypstText` 而言，作为索引的字符串不在公式环境中

    这里给出几段示例作为参考：

    .. code-block:: python

        t = TypstMath('cos theta')
        t['theta']

        t = TypstText('$ cos theta $')
        t['$theta$']

    .. code-block:: python

        t = TypstText('this is a formula: $cos^2 x + sin^2 x = 1$')
        t['formula']
        t['$x$']

内置包
-----------------

JAnim 提供了内置包可以在 Typst 中使用 ``#import`` 引入

- ``#import "@janim/colors:0.0.0": *``

  提供了 JAnim 中的颜色常量（可参考 :ref:`constants_colors` 条目），以便在 Typst 中使用

  .. raw:: html

    <details>
    <summary>点击展开 @janim/colors 的具体定义</summary>

  .. code-block:: typst

      // Colors
      #let BLUE_E = rgb("#1C758A")
      #let BLUE_D = rgb("#29ABCA")
      #let BLUE_C = rgb("#58C4DD")
      #let BLUE_B = rgb("#9CDCEB")
      #let BLUE_A = rgb("#C7E9F1")
      #let TEAL_E = rgb("#49A88F")
      #let TEAL_D = rgb("#55C1A7")
      #let TEAL_C = rgb("#5CD0B3")
      #let TEAL_B = rgb("#76DDC0")
      #let TEAL_A = rgb("#ACEAD7")
      #let GREEN_E = rgb("#699C52")
      #let GREEN_D = rgb("#77B05D")
      #let GREEN_C = rgb("#83C167")
      #let GREEN_B = rgb("#A6CF8C")
      #let GREEN_A = rgb("#C9E2AE")
      #let YELLOW_E = rgb("#E8C11C")
      #let YELLOW_D = rgb("#F4D345")
      #let YELLOW_C = rgb("#FFFF00")
      #let YELLOW_B = rgb("#FFEA94")
      #let YELLOW_A = rgb("#FFF1B6")
      #let GOLD_E = rgb("#C78D46")
      #let GOLD_D = rgb("#E1A158")
      #let GOLD_C = rgb("#F0AC5F")
      #let GOLD_B = rgb("#F9B775")
      #let GOLD_A = rgb("#F7C797")
      #let RED_E = rgb("#CF5044")
      #let RED_D = rgb("#E65A4C")
      #let RED_C = rgb("#FC6255")
      #let RED_B = rgb("#FF8080")
      #let RED_A = rgb("#F7A1A3")
      #let MAROON_E = rgb("#94424F")
      #let MAROON_D = rgb("#A24D61")
      #let MAROON_C = rgb("#C55F73")
      #let MAROON_B = rgb("#EC92AB")
      #let MAROON_A = rgb("#ECABC1")
      #let PURPLE_E = rgb("#644172")
      #let PURPLE_D = rgb("#715582")
      #let PURPLE_C = rgb("#9A72AC")
      #let PURPLE_B = rgb("#B189C6")
      #let PURPLE_A = rgb("#CAA3E8")
      #let GREY_E = rgb("#222222")
      #let GREY_D = rgb("#444444")
      #let GREY_C = rgb("#888888")
      #let GREY_B = rgb("#BBBBBB")
      #let GREY_A = rgb("#DDDDDD")

      #let PURE_RED = rgb("#FF0000")
      #let PURE_GREEN = rgb("#00FF00")
      #let PURE_BLUE = rgb("#0000FF")

      #let WHITE = rgb("#FFFFFF")
      #let BLACK = rgb("#000000")
      #let GREY_BROWN = rgb("#736357")
      #let DARK_BROWN = rgb("#8B4513")
      #let LIGHT_BROWN = rgb("#CD853F")
      #let PINK = rgb("#D147BD")
      #let LIGHT_PINK = rgb("#DC75CD")
      #let GREEN_SCREEN = rgb("#00FF00")
      #let ORANGE = rgb("#FF862F")

      // Be compatible with the old names
      #let GREEN_SCREEN = rgb("#00FF00")

      // Abbreviated names for the "median" colors
      #let BLUE = BLUE_C
      #let TEAL = TEAL_C
      #let GREEN = GREEN_C
      #let YELLOW = YELLOW_C
      #let GOLD = GOLD_C
      #let RED = RED_C
      #let MAROON = MAROON_C
      #let PURPLE = PURPLE_C
      #let GREY = GREY_C

  .. raw:: html

      </details>

.. note::

    如果你需要脱离 JAnim 在外部 ``.typ`` 文件中编写 Typst 代码，希望其也能引入 JAnim 的内置包

    你需要将 ``<site-packages>/janim/items/svg`` 完整路径通过 ``--package-path`` 选项传递给 Typst 编译器或 Tinymist 插件的 ``"tinymist.typstExtraArgs"`` 选项

语法高亮
----------------

前面提到，如果你使用了 VSCode 插件 ``janim-toolbox``，
会自动给 :class:`TypstDoc` 和 :class:`TypstText` 中出现的 Raw-字符串（形如 ``R'...'``） 进行 Typst 语法高亮。

对于同样需要 Typst 语法高亮，但不在 :class:`TypstDoc` 与 :class:`TypstText` 之中的字符串，你可以使用 ``t_`` 函数来标注需要 Typst 高亮，例如

.. code-block:: python

    LightTyp = partial(TypstText, color=YELLOW)

    typ = LightTyp(t_(R'#box(width: 10em)[#lorem(20)]')).show()

.. code-block:: python

    with Config(typst_shared_preamble='#set box(width: 3em, height: 3em)'):
        group = Group.from_iterable(
            TypstText(content) for content in t_(
                R'#box(stroke: red)',
                R'#box(fill: red)',
                R'#box(stroke: red, outset: 2pt)[ab]',
                R'#box(fill: aqua)[A]',
            )
        )

    group.points.arrange()
    group.show()

嵌入 JAnim 物件
----------------------

Typst 物件支持传入 ``vars`` 参数嵌入 JAnim 物件：

.. janim-example:: TypstVars
    :media: _static/tutorial/TypstVars.mp4
    :hide_name:
    :ref: :class:`~.TypstText` :class:`~.Video`

    typ1 = TypstText(
        R'This is a sentence with an inserted #star JAnim item',
        vars={
            'star': Star(outer_radius=0.5, color=YELLOW, fill_alpha=0.5)
        },
        vars_size_unit='em'
    )

    typ2 = TypstText(
        R'''
        #box(fill: luma(40%), inset: 8pt)[
            This is a grid containing JAnim items
            #grid(
                columns: 2,
                fill: luma(20%),
                gutter: 4pt,
                inset: 8pt,

                [$f(x)$\ math content],
                gif,
                star,
                [QwQ\ text content]
            )
        ]
        ''',
        vars={
            'gif': Video('Ayana.gif', loop=True).start(),
            'star': Star(),
        },
    )

    Group(typ1, typ2).show().points.arrange(DOWN)
    self.forward(4)

.. hint::

    未传入 ``vars_size_unit`` 时，嵌入的 JAnim 物件会保留在 JAnim 中原有的大小，若传入了 ``vars_size_unit`` 则将其大小乘上对应的单位。

    例如对于一个在 JAnim 中高度为 1 的物件，如果直接插入 Typst 文字中会显得很大，此时设置 ``vars_size_unit='em'`` 使其插入高度变为 ``1em``，则基本与文字高度匹配。

``vars`` 是一个字典，它的键会作为 Typst 代码中可以使用的变量名，值会作为变量名对应的 JAnim 物件，并且支持进一步嵌套列表和字典：

.. code-block:: python

    TypstText(
        ...,
        vars=dict(
            shapes=[
                Star(),
                Square(),
                Circle()
            ],
            mapping=dict(
                txt=Text('This is a JAnim sentence'),
                vid=Video('example.mp4').start()
            )
        )
    )

.. note::

    在 Typst 中嵌入 JAnim 物件，从原理上来讲是创建了一个对应大小的占位 ``box``，然后在 Typst 物件创建后，将其替换为 JAnim 物件，从而做到嵌入的目的。

标记基点位置
----------------------

标记基点位置的功能默认是关闭的，如果你希望给 Typst 物件的每个元素都标记基点位置，可以通过传入 ``mark_basepoint=True`` 来开启该功能：

.. code-block:: python

    TypstText('This is a sentence', mark_basepoint=True)

.. janim-example:: TypstMarkBasepoint
    :media: _static/images/typ_mark.png
    :hide_name:

    typ = TypstText('Ggf', scale=4, mark_basepoint=True, fill_alpha=0.5).show()

    for elem in typ:
        orig, right, up = elem.mark.get_points()
        right = orig + 4 * (right - orig)
        up = orig + 4 * (up - orig)

        Arrow(orig, right, buff=0, color=BLUE).show()
        Arrow(orig, up, buff=0, color=BLUE).show()
        Dot(orig, 0.06, fill_color=BLACK, stroke_color=BLUE, stroke_alpha=1).show()


关于基点位置的使用，请参考 :class:`~.BasepointVItem`。

.. note::

    ``mark_basepoint`` 其实是 :class:`~.SVGItem` 提供的一个参数，但是由于我们主要在 Typst 物件中使用它，所以放在这里进行说明。

特殊类型的 Typst 物件
-----------------------------

- :class:`~.TypstMatrix` 使用 Typst 进行矩阵布局

参考文档
-------------

- JAnim 类定义：请参考 :ref:`typst` 页面
- Typst 中文社区： `typst-doc-cn.github.io/guide <https://typst-doc-cn.github.io/guide>`_
- Typst 官方文档： `typst.app/docs <https://typst.app/docs>`_
