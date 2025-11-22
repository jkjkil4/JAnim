.. _get_started:

入门
======

简单示例
------------

为了让你对 JAnim 的结构有个大概的认知，
你可以在你的文件夹内新建一个 ``learn.py`` 文件

然后将以下代码复制到文件内：

.. janim-example:: HelloJAnimExample
    :media: _static/videos/HelloJAnimExample.mp4

    from janim.imports import *

    class HelloJAnimExample(Timeline):
        def construct(self):
            # 定义物件
            circle = Circle(color=BLUE)
            square = Square(color=GREEN, fill_alpha=0.5)

            # 进行动画
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
        def construct(self):

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
    | 将方形设置为了绿色，并且设置内部有 50% 透明度的填充

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
    - ``self.play(Create(circle))`` 播放圆的创建动画
    - ``self.play(Transform(circle, square))`` 播放从圆变换到方形的补间动画
    - ``self.play(Uncreate(square))`` 播放方形消失的动画
    - ``self.forward()`` 向前推进 1s，和前一个类似

其中：

- :meth:`~.Timeline.forward` 将相同的画面持续一段时间，默认是 1s，你也可以填入具体的秒数
- :meth:`~.Timeline.play` 的基本格式是 ``self.play(动画对象)``，让动画持续一段时间

比如，你可以把变换的那一行加上 ``duration=2``

.. code-block:: python

    self.play(Transform(circle, square), duration=2)

那么动画过程就会持续 2s

物件
------------

上面的例子中，涉及到两个物件：:class:`~.Circle` 和 :class:`~.Square`，它们本质上都是几何图形物件

组件
~~~~~~~~~~~~

.. important::

    对于物件，有一个重要的概念是“组件”

    | 每种物件都包含若干的组件，例如，几何图形其实是由“轮廓的描点”所表示的，
    | 因此，对于几何图形物件，这些是它的组件：

    - 轮廓坐标 ``points``
    - 描边粗细 ``radius``
    - 描边颜色 ``stroke``
    - 填充颜色 ``fill``

为了对组件进行操作，你需要 ``物件.组件名.功能()`` ，比如：

.. code-block:: python

    circle.fill.set(RED, 0.5)

这一行会将圆的填充色设置为红色，并且有 50% 的透明度；你可以把这行插入到上面例子的 ``circle = Circle(color=BLUE)`` 的下一行，试试效果

同样的，``circle.stroke.set(...)`` 会设置描边的颜色

.. hint::

    如果你想将描边和填充的颜色同时进行设置，不必写：

    .. code-block::

        circle.stroke.set(RED)
        circle.fill.set(RED)

    作为一种更简便的写法，你可以将上面的两行写成这样：

    .. code-block::

        circle.color.set(RED)

    这里提供了一个 ``color``，可以同时对描边和填充进行操作

初始化参数
~~~~~~~~~~~~

还记得前面例子的代码吗？

.. code-block::

    # 定义物件
    circle = Circle(color=BLUE)
    square = Square(color=GREEN, fill_alpha=0.5)

这里的代码看起来没有对 ``circle`` 的组件进行操作，那么是如何设置这些物件的颜色的呢？

你应该注意到了传入 :class:`~.Circle` 和 :class:`~.Square` 的参数，``color=XXX`` 以及 ``fill_alpha=XXX``

具体来说，在创建物件时对组件属性进行设置，并不需要一行一行地列出来，可以全部作为参数直接书写，这里列出几何图形物件可用的一些属性：

.. TODO: 链接到颜色表

- ``stroke_radius``: 描边的粗细

- ``color``: 描边和填充的颜色
- ``stroke_color``: 描边颜色，会覆盖 ``color``
- ``fill_color``: 填充颜色，会覆盖 ``color``

- ``alpha``: 透明度，``1`` 表示完全不透明，``0`` 表示完全透明，``0~1`` 之间的数则为半透明
- ``stroke_alpha``: 描边透明度，会覆盖 ``alpha``
- ``fill_alpha``: 填充透明度，会覆盖 ``alpha``

组件动画
------------

通过前面的学习，我们知道，通过

.. code-block::

    circle.color.set(RED)

可以将圆设置为红色

这种设置是立刻的，但是如果这样写：

.. code-block::

    circle.anim.color.set(RED)

注意这里的区别是，先写 ``.anim`` 再跟上对组件的操作

这种写法，不再是“设置为红色”，而是会产生一个“从原来的颜色过渡到红色”的动画，可以放在 ``self.play(...)`` 里面显示动画

比如下面这个例子：

.. janim-example:: CmptAnimExample
    :media: _static/videos/CmptAnimExample.mp4

    from janim.imports import *

    class CmptAnimExample(Timeline):
        def construct(self) -> None:
            circle = Circle(color=BLUE, fill_alpha=0.5)

            self.show(circle)
            self.forward()
            self.play(circle.anim.color.set(GREEN))
            self.play(circle.anim.fill.set(alpha=0.2))
            self.play(circle.anim.points.scale(2))
            self.forward()

.. note::

    ``self.show(circle)`` 是将圆直接显示出来，没有动画过程

希望你没忘记，执行的命令是：

.. code-block:: sh

    janim run 文件名 时间轴名

如果上面这段代码也写在了 ``learn.py`` 中，那么就是：

.. code-block:: sh

    janim run learn.py CmptAnimExample

导出视频
------------

.. warning::

    若要导出视频，请确保安装了 :ref:`FFmpeg <install_dep>` 并正确地将其添加到了环境变量 ``PATH`` 中

上面进行预览是使用：

.. code-block:: sh

    janim run learn.py CmptAnimExample

如果你想要将这个动画导出为视频，将 ``run`` 替换为 ``write`` 即可：

.. code-block:: sh

    janim write learn.py CmptAnimExample

默认情况下，输出的视频会在目录中的 ``videos/`` 文件夹下

如果再传入 ``-o``，会在导出结束后自动打开视频文件：

.. code-block:: sh

    janim write learn.py CmptAnimExample -o

.. _realtime_preview:

实时预览
------------

如果每次修改动画都需要关掉窗口、修改代码、重新执行，那么未免有点太麻烦了

因此，你可以在修改并保存代码后，点击窗口左上角“文件”中的“重新构建”（快捷键是 ``Ctrl+L``），
这样就会更新动画内容，使其和更改后的代码一致

.. warning::

    以下的功能需要使用 :ref:`VS Code <install_vscode>` 作为编辑器

每次修改完都要手动重新构建可能还是有点麻烦了，如果你使用 VS Code 开发，可以安装 VS Code 插件 ``janim-toolbox``

运行时，在预览动画的命令中加上 ``-i``，比如：

.. code-block:: sh

    janim run learn.py CmptAnimExample -i

这样，在执行后，输出内容应当多出这样一句：``交互端口已在 xxxxx 开启``

.. tip::

    你可能注意到了，预览窗口默认是在右半边屏幕置顶的

    这里推荐将 VS Code 放在左半边屏幕，关闭侧边栏进行书写

首先，在 VS Code 中，默认情况下，需要按下 ``Ctrl+J Ctrl+C`` （分别按下，这是组合键），如果成功的话，
会在 VS Code 右下角的状态栏中显示 ``已连接到界面端 xxxxx``

接着，对代码进行更改，保存后，就会立即更新预览的内容
