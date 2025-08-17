Typst 的使用
======================

简要介绍
---------------------

如果你是从 Manim 迁移过来的用户，你可能对 LaTeX 有一定的了解。

当我们在 JAnim 中使用 Typst，就像是在 Manim 中使用 LaTeX，可以通过代码的形式创建排版或公式。

我们常用 :class:`~.TypstText` 和 :class:`~.TypstMath` 来在 JAnim 中使用 Typst

.. code-block:: python

    typ1 = TypstText(R'This is a #text(aqua)[sentence] with a math expression $f(x)=x^2$')
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

也就是说，:class:`~.TypstText` 和 :class:`~.TypstMath` 的区别仅是是否被包裹在公式环境中，例如 ``TypstMath('x^2')`` 和 ``TypstText('$ x^2 $')`` 是在大多数情况下是等效的

