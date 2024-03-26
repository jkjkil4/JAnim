入门
======

简单示例
------------

为了让你对 JAnim 的结构有个大概的认知，
你可以在你的文件夹内新建一个 ``learn.py`` 文件

然后将以下代码复制到文件内：

.. janim-example:: HelloJAnimExample
    :media: ../_static/videos/HelloJAnimExample.mp4

    from janim.imports import *

    class HelloJAnimExample(Timeline):
        def construct(self) -> None:
            # define items
            circle = Circle(color=BLUE)
            square = Square(color=GREEN, fill_alpha=0.5)

            # do animations
            self.forward()
            self.play(Create(circle))
            self.play(Transform(circle, square))
            self.play(Uncreate(square))
            self.forward()

接着在命令行中，使用

.. code-block:: sh

    janim run learn.py HelloJAnimExample

会弹出一个窗口，应当会显示和上面视频一致的内容

这个窗口默认是置顶的，你可以在菜单栏中取消

然后，我们具体看一下这段代码干了什么：

.. code-desc::

    from janim.imports import *

    %

    这里，我们引入 JAnim 的主要功能，这样就可以在之后使用

.. code-desc::

    class HelloJAnimExample(Timeline):
        def construct(self) -> None:

    %

    这两行代码定义了一个继承自 :class:`~.Timeline` 的类 ``HelloJAnimExample``，
    并且实现了 :meth:`~.Timeline.construct` 方法，动画内容就写在该方法中

    ``HelloJAnimExample`` 可以写成你想取的名称，随意

.. tip::

    如果你对这两行感到困惑，可以先背下来，作为一种标准的“起手式”

    当然，请将 ``HelloJAnimExample`` 替换为你希望的命名

我们继续往下看，便是具体动画的部分

.. code-desc::

    circle = Circle(color=BLUE)
    square = Square(color=GREEN, fill_alpha=0.5)

    %

    这两行，我们定义了一个圆和一个方形（默认情况下不填充内部）

    | 并且，将圆设置为了蓝色；
    | 将方形设置为了蓝色，并且设置内部有 50% 透明度的填充

此时，这两个物件还没有显示出来，我们接着看后面的几行

.. code-desc::

    self.forward()
    self.play(Create(circle))
    self.play(Transform(circle, square))
    self.play(Uncreate(square))
    self.forward()

    %

    这里便是产生动画的代码，按照顺序来看：

    - ``self.forward()`` 向前推进 1s；由于此时没有物件显示，所以这 1s 只有空白的背景
    - ``self.play(Create(circle))`` 显示圆的创建动画
    - ``self.play(Transform(circle, square))`` 显示从圆变换到方形的补间动画
    - ``self.play(Uncreate(square))`` 显示方形消失的动画
    - ``self.forward()`` 向前推进 1s，和前一个类似

其中：

- :meth:`~.Timeline.forward` 将相同的画面持续一段时间，默认是 1s，你也可以填入具体的秒数
- :meth:`~.Timeline.play` 的基本格式是 ``self.play(动画对象)``，让动画持续一段时间

比如，你可以把变换的那一行加上 ``duration=2``

.. code-block:: python

    self.play(Transform(circle, square), duration=2)

那么动画过程就会持续 2s
