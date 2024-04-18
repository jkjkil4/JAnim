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

.. raw:: html

    <del>有点像 FPS 游戏的键位</del>

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

重新构建
~~~~~~~~~~~~

已在 :ref:`实时预览 <realtime_preview>` 中提及

.. _subitem_selector:

子物件选择
~~~~~~~~~~~~

对于子物件复杂的物件（比如 :class:`~.Text` 和 :class:`~.Typst`），
取其切片就会比较麻烦，因此预览界面提供了进行子物件选择的功能

点击窗口左上角“功能”中的“子物件选择”，左上角会多出这样的内容：

.. image:: /_static/images/subitem_selector1.png
    :align: center
    :scale: 65%

首先，如果说我们需要取出一行文本 :class:`~.TextLine` 的某一些字符，我们需要首先找到这行文本，
那么可以使用 ``Ctrl+左键`` 点击进行选中

.. hint::

    为了选中 :class:`~.TextLine`，由于它是 :class:`~.Text` 的子物件，所以点击一下后，首先会选中整段文本，我们再点击一下便可以选中这一行的 :class:`~.TextLine`

.. image:: /_static/images/subitem_selector2.png
    :align: center
    :scale: 65%

选中这行文本后，松开按着 ``Ctrl`` 的手，直接用 ``左键`` 点击这行文本中的字符（可以长按扫动），就可以选出它们，左上角会显示对应的下标

.. image:: /_static/images/subitem_selector3.png
    :align: center
    :scale: 65%

.. note::

    这里选中的是 "first" 和 "ne"，对应的切片是 ``[4:9]`` 和 ``[12:14]``

如果选多了，可以 ``右键`` 取消

选择完后，使用 ``Ctrl+右键`` 退出这个功能

富文本编辑
~~~~~~~~~~~~

这是针对编辑 :ref:`富文本格式 <rich_text>` 而实现的功能

在这个编辑器中，富文本标签会被高亮，提高可读性

.. warning::

    实验性功能：粘贴时识别富文本格式

    该选择框启用后，会尝试将粘贴的 html 文本样式转换为 JAnim 富文本样式
