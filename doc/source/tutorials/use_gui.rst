界面使用
============

基本介绍
------------

界面元素
~~~~~~~~~~~~

.. image:: /_static/images/use_gui.png
    :align: center
    :scale: 50%

如上图，整个界面主要分为两个部分

- 上面黑色背景的这块是显示画面
- 下面带有各个动画标签的是时间轴

进度控制
~~~~~~~~~~~

| 按下空格键控制播放和暂停
| 如果播放到了末尾按下空格键，会从头播放

也可以在时间轴中左键拖动当前时刻，调整到你要查看的地方

时间轴显示区段控制
~~~~~~~~~~~~~~~~~~~~~~~~

你可以使用 “WASD” 来控制在时间轴上的区段：

.. list-table::

    *   -
        -   W 放大
        -
    *   -   A 左移
        -   S 缩小
        -   D 右移

有点像 FPS 游戏的键位

.. _window_position:

窗口位置
~~~~~~~~~~~~

默认的窗口位置是占据右半边屏幕，你可以通过自定义配置来更改

你可以修改全局配置，在命令行参数中加上 ``-c wnd_pos UR``，比如：

.. code-block:: sh

    janim run your_file.py YourTimeline -c wnd_pos UR

.. note::

    修改全局配置的格式是 ``-c 配置名 值``，更多的配置请参考 :class:`~.Config`

``UR`` 表示 ``UP & RIGHT``，即窗口占据屏幕右上角

也就是说，前一个字符表示在纵向的位置，后一个字符表示在横向的位置

以下是可用的位置字符（括号内表示这个字符的含义）：

.. list-table::

    *   -   U (UP)
        -   上方
    *   -   O
        -   占据整个纵向长度
    *   -   D (DOWN)
        -   下方

.. list-table::

    *   -   L (LEFT)
        -   O
        -   R (RIGHT)
    *   -   左侧
        -   占据整个横向长度
        -   右侧

除了修改全局配置，你也可以修改时间轴配置，请参考：:class:`~.Config`

进阶功能
------------

具体信息
~~~~~~~~~~~~

鼠标悬停在时间轴动画标签上可以显示具体信息，例如时间区段、插值函数散点图等

.. image:: /_static/images/hover_at_timeline.png
    :align: center
    :scale: 50%

.. _vscode_extension:

VS Code 插件
~~~~~~~~~~~~

可在 VS Code 中安装 ``janim-toolbox`` 插件，提供了一些额外的功能

- 重新构建：已在 :ref:`realtime_preview` 中提及；关于多文件重新构建时的处理，另见 :func:`~.reloads`

- 当前行高亮：编辑器中会高亮显示当前动画的代码行

- 自动定位：随着预览窗口中动画的播放，自动定位到当前的代码行，默认情况下可以使用 ``Ctrl+J Ctrl+A`` 启用/关闭自动定位

- 手动定位：默认情况下可以使用 ``Ctrl+J Ctrl+L`` 手动定位到当前的代码行

.. _subitem_selector:

子物件选择
~~~~~~~~~~~~

对于子物件复杂的物件（比如 :class:`~.Text` 和 :class:`~.TypstMath`），
取其切片就会比较麻烦，因此预览界面提供了进行子物件选择的功能

点击窗口左上角“工具”中的“子物件选择”，左上角会多出这样的内容：

.. image:: /_static/images/subitem_selector1.png
    :align: center
    :scale: 45%

首先，如果说我们需要取出一行文本 :class:`~.TextLine` 的某一些字符，我们需要首先找到这行文本，
那么可以使用 ``Ctrl+左键`` 点击进行选中

.. hint::

    为了选中 :class:`~.TextLine`，由于它是 :class:`~.Text` 的子物件，所以点击一下后，首先会选中整段文本，我们再点击一下便可以选中这一行的 :class:`~.TextLine`

.. image:: /_static/images/subitem_selector2.png
    :align: center
    :scale: 45%

选中这行文本后，松开按着 ``Ctrl`` 的手，直接用 ``左键`` 点击这行文本中的字符（可以长按扫动），就可以选出它们，左上角会显示对应的下标

.. image:: /_static/images/subitem_selector3.png
    :align: center
    :scale: 45%

.. note::

    这里选中的是 "first" 和 "ne"，对应的切片是 ``[4:9]`` 和 ``[12:14]``

如果选多了，可以 ``右键`` 取消

选择完后，使用 ``Ctrl+右键`` 退出这个功能

绘制
~~~~~~~~~~~

为了方便在界面上取坐标以供参考，提供了“绘制”功能：

- ``Dot``: 选择后，点击屏幕可以在工具窗口中得到一个坐标

.. image:: /_static/images/f_draw_dot.png
    :align: center
    :scale: 50%

- ``Rect``: 选择后，在画面上按下，然后拖动，再抬起，会根据起止点得到一个矩形

.. image:: /_static/images/f_draw_rect.png
    :align: center
    :scale: 50%

- ``VItem``: 选择后，在画面上绘制，可以得到一段曲线；一般情况下顶点会比较多，可以使用拖动条减少点的数量并平滑化

.. image:: /_static/images/f_draw_vitem.png
    :align: center
    :scale: 50%

可以同时取多个物件，不同物件会在工具界面上对应多个分页：

.. image:: /_static/images/f_draw_pages.png
    :align: center
    :scale: 50%

.. warning::

    这些仅是在屏幕上确定位置用的，为了将绘制出的东西真正地加进去，你需要手动添加对应的代码

如果没有选择任何选项（也就是“无”），在画面上拖动将会控制当前页的物件位置

富文本编辑
~~~~~~~~~~~~

这是针对编辑 :ref:`富文本格式 <rich_text>` 而实现的功能

在这个编辑器中，富文本标签会被高亮，提高可读性

.. warning::

    实验性功能：粘贴时识别富文本格式

    该选择框启用后，会尝试将粘贴的 html 文本样式转换为 JAnim 富文本样式

.. tip::

    可以在命令行使用 ``janim tool richtext`` 单独打开该界面

字体列表
~~~~~~~~~~~~~

.. image:: /_static/images/font_table.png
    :align: center
    :scale: 65%

提供了字体索引列表，方便查找字体

- 其中“字体族名”和“全名”都是可以传给 :class:`~.Text` 的 ``font`` 参数，例如：

.. code-block:: python

    Text(..., font='LXGW WenKai Lite')
    Text(..., font='LXGW WenKai Lite', weight='light')
    Text(..., font='LXGW WenKai Lite Light')

- 善用搜索功能，可以方便地根据字体名称进行查找

.. tip::

    可以在命令行使用 ``janim tool fonts`` 单独打开该界面

颜色
~~~~~~~~~~~

.. image:: /_static/images/color_table.png
    :align: center
    :scale: 65%

提供了便捷的颜色输入、转换、预览和选取的功能

.. tip::

    可以在命令行使用 ``janim tool color`` 单独打开该界面
