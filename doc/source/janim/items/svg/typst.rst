typst
=====

Typst 物件
--------------------

Typst 物件分为三种：

- :class:`~.TypstDoc` 是所有其它 Typst 物件的基类，它表示一个 Typst 文档

  这意味着，它会自动与画面的最上方对齐，以便从文档的开头开始查看

- :class:`~.TypstText` 表示 Typst 文字，传入的字符串不会被 ``$ $`` 所包裹

  它会直接被放到画面的中间

- :class:`~.TypstMath` 表示 Typst 公式，传入的字符串会被包裹在 ``$ $`` 中作为公式进行编译

  它会直接被放到画面的中间

也就是说，:class:`~.TypstText` 和 :class:`~.TypstMath` 的区别仅是是否被包裹在公式环境中，例如 ``TypstMath('x^2')`` 和 ``TypstText('$ x^2 $')`` 是等效的

Typst 子物件索引
------------------------------

我们知道，对于一般的对象可以使用下标索引或者布尔索引

.. note::

    以防你不知道，这里补充一下

    - 下标索引，例如 ``t[0]``， ``t[1]``，这是常用的子物件索引方式

      还有 ``t[0, 1, 4]`` 表示取出指定索引的多个子物件

    - 布尔索引，例如 ``t[False, True, False, True, True]`` 表示取出 ``Group(t[1], t[3], t[4])``，

      也就是将那些为 True 的位置取出组成一个 :class:`~.Group`

当你要索引 Typst 对象的子物件时，还可以使用字符索引的方式，比如说对于 :class:`~.TypstMath` 对象 ``t`` 而言

.. code-block:: python

    t = TypstMath('cos^2 theta + sin^2 theta = 1')

可以使用 ``t['cos']`` 得到 cos 对应的部分，这样你可以就可以使用类似于 ``t['cos'].set(color=BLUE)`` 的方式进行着色

当出现多个匹配时的处理
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

你应该注意到了这里有两个 "θ"（``theta``），当你使用 ``t['theta']`` 的方式进行索引时，将会取出第一个匹配的 θ，也就是前一个

因为他们是从 ``0``、 ``1``、... 依次编号的，所以你可以使用 ``t['theta', 1]`` 得到后一个，如果有更多的匹配则是使用更后面的序号

.. note::

   这也意味着 ``t['theta']`` 和 ``t['theta', 0]`` 是等效的

如果想要同时取出多个，则将多个编号写在一个序列中即可，例如 ``t['theta', (0, 1)]`` 则是取出编号为 ``0`` 和 ``1`` 的匹配项，在这里就是所有匹配到的 θ 符号

对于这种取出所有匹配项的情况，也可以使用 ``t['theta', ...]``，这里的省略号就表示取出所有的匹配项

一些特殊情况
~~~~~~~~~~~~~~~~~~~~

当你想要取出这个 Typst 公式中的上标 "2" 时

使用 ``t['2']`` 无法匹配到它，这是因为普通的 "2" 和上标的 "2" 长得不同

为了正确匹配，你需要把索引中的 2 也表示为“上标”的形式，例如 ``t['""^2']`` 或者 ``t['#box[]^2']``

这两者都是把 "2" 作为一个空元素（ ``""`` 或者 ``#box[]`` ）的上标，这样就可以正常匹配了

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
----------------

JAnim 提供了内置包可以在 Typst 中使用 ``#import`` 进行引入

- ``#import "@janim/colors:0.0.0": *``

  提供了 JAnim 中的颜色常量，以便在 Typst 中使用

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

.. note::

    如果你需要在外部 ``.typ`` 文件中也能引入 JAnim 的内置包

    你需要将 ``<site-packages>/janim/items/svg`` 完整路径通过 ``--package-path`` 选项传递给 Typst 编译器或 Tinymist 插件的 ``"tinymist.typstExtraArgs"`` 选项

其它
------------

如果你使用了 VSCode 插件 ``janim-toolbox``，
会自动给 :class:`TypstDoc` 和 :class:`TypstText` 中出现的 raw 字符串（形如 ``R'...'``） 进行 Typst 语法高亮，例如

.. code-block:: python

    typ = TypstText(R'#box(width: 10em)[#lorem(20)]').show()

.. note::

  该页面中没有效果，你可以将代码复制到编辑器中试一试

对于同样需要 Typst 语法高亮的函数，你可以使用 ``t_`` 函数来标注需要 Typst 高亮，例如

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

参考文档
------------

.. automodule:: janim.items.svg.typst
   :members:
   :undoc-members:
   :show-inheritance:

