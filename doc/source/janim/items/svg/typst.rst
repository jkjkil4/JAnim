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

可以使用 ``t['cos']`` 得到 cos 对应的部分，这样你可以就可以使用类似于 ``t['cos'].digest_styles(color=BLUE)`` 的方式进行着色

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

参考文档
------------

.. automodule:: janim.items.svg.typst
   :members:
   :undoc-members:
   :show-inheritance:

