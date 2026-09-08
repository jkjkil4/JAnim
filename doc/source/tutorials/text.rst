简易文字物件
===========================

上一节中我们提到可以使用 Typst 进行文字和公式的书写与排版，
而对于及为简单的显示普通文字的需求，也可以使用这一节介绍的 :class:`~.Text` 来创建。

文字物件的结构
------------------

文字物件的结构比较复杂，:class:`~.Text` 包含若干个 :class:`~.TextLine`，每个 :class:`~.TextLine` 包含若干个 :class:`~.TextChar`

比如，对于

.. code-block:: python

   txt = Text('The first line.\nThe second line.\nThe third line.')

那么下图便说明了它的子物件情况， ``txt[0]`` 、 ``txt[1]`` 和 ``txt[2]`` 都是 :class:`~.TextLine`

.. image:: /_static/images/text_children.png
   :align: center
   :scale: 50%

对于每个 :class:`~.TextLine` 而言，比如 ``txt[0]``，其子物件情况是如下图这样的

.. image:: /_static/images/textline_children.png
   :align: center
   :scale: 60%

.. hint::

   其中 ``txt[0][3]`` 和 ``txt[0][9]`` 是空格

也就是说这是一个 :class:`~.Text` → :class:`~.TextLine` → :class:`~.TextChar` 的嵌套结构

对于这种复杂的嵌套结构，如果你想要取子物件列表的切片，手动数数可能有点繁琐（比如上面例子的首行中，"first" 对应的切片是 ``[4:9]``）

为了解决这个问题，你可以参考预览界面的 :ref:`subitem_selector` 功能

字符的标记属性
------------------

:class:`~.TextChar` 有四个标记属性，比如对于 “Ggf” 中的 “g” 字符而言：

.. image:: /_static/images/char_mark.png
   :align: center
   :scale: 50%

- :meth:`~.TextChar.get_mark_orig` 是字符在基线上的原点
- :meth:`~.TextChar.get_mark_right` 是对字符水平右方向的标记
- :meth:`~.TextChar.get_mark_up` 是对字符竖直上方向的标记
- :meth:`~.TextChar.get_mark_advance` 指向下一个字符的 ``orig``

.. note::

   :class:`~.TextLine` 也有类似的结构，但是只有 ``orig`` 、 ``right`` 和 ``up``，没有 ``advance``

有关更多与基线原点有关的内容，请参考 :class:`~.BasepointVItem` 。

.. _rich_text:

富文本
-----------

可以使用起始标记和结束标记（像 HTML 那样的）应用富文本格式：

具体写法是： ``<格式名 参数>被应用对应格式的文本</格式名>``

比如，要想让文字的一部分变为蓝色，可以这样书写：

.. code-block:: python

   Text('Hello <c BLUE>JAnim</c>!', format=Text.Format.RichText)

``format=Text.Format.RichText`` 也可以简写为 ``format='rich'``

.. code-block:: python

   Text('Hello <c BLUE>JAnim</c>!', format='rich')

.. note::

   这里的 ``c`` 是 ``color`` 的简写

.. important::

   :class:`~.Text` 使用富文本需要传入 ``format=Text.Format.RichText`` 或者 ``format='rich'`` ，否则默认情况下视作普通文本

以下列出了可用的格式：

.. list-table::

   *  - 名称
      - 缩写
      - 作用
      - 参数
      - 示例
      - 备注
   *  - color
      - c
      - 颜色
      - 颜色名称
      - ``<c BLUE>JAnim</c>``
      -
   *  -
      -
      -
      - 十六进制值
      - ``<c #00ff00>JAnim</c>``
      -
   *  -
      -
      -
      - r g b
      - ``<c 0 1.0 0.5>JAnim</c>``
      -
   *  -
      -
      -
      - r g b a
      - ``<c 0 1.0 0.5 0.5>JAnim</c>``
      - 描边也被设置为半透明
   *  - stroke_color
      - sc
      - 描边颜色
      - 同上
      -
      -
   *  - fill_color
      - fc
      - 填充颜色
      - 同上
      -
      -
   *  - alpha
      - a
      - 透明度
      - 一个数
      - ``<a 0.5>JAnim</a>``
      - 描边也被设置为半透明
   *  - stroke_alpha
      - sa
      - 描边透明度
      - 同上
      -
      -
   *  - fill_alpha
      - fa
      - 填充透明度
      - 同上
      -
      -
   *  - stroke
      - s
      - 描边半径
      - 一个数
      - ``<s 0.01>JAnim</s>``
      -
   *  - font_scale
      - fs
      - 缩放倍数
      - 一个数
      - ``Hello <fs 1.2>JAnim</fs>``
      -

.. tip::

   如果你想直接输入 ``<`` 符号，不希望其被解析为富文本标记，可以使用 ``<<`` 来表示一个 ``<`` 符号，例如：

   .. code-block:: python

      Text('if x << 10 <c RED>and</c> x > 2:', format='rich')

性能优化
------------------------

每个字符物件都是一个 :class:`~.VItem` ，存储了字形的复杂轮廓，这导致字符物件在渲染时性能低下，且在移动、旋转等变换时，由于字形大量变化，更加导致卡顿。

如果你在某些场景，比如 **展示大量文段或代码** 等场景中，确定使用的 :class:`~.Text` 不涉及复杂的变换，只涉及移动和旋转，
你可以给 :class:`~.Text` 传入 ``render='pixel'`` 使用位图模式进行字符渲染，例如

.. code-block:: python

   Text('Hello!', render='pixel')

这会极大地改善文字渲染的性能。

当然，使用 ``render='pixel'`` 提升文字渲染的性能后，所创建出的 ``Text`` 的功能也会被削弱，例如：

- 对于其中的字符物件， ``.points.get()`` 不再是字形轮廓数据，而是表征边界框的数个点，按照方向排列为 ``[DL, DR, UR, UL, DL]``

- 字符物件的描边属性无效，仅渲染填充色

- 无法进行复杂的顶点变换，在非线性变换后仍然保持原来的位图形状

- 无法正常和其它图形物件之间进行 :class:`~.Transform` 动画

- 文字渲染的分辨率会依照接近初次指定的字号进行采样，这意味着放大可以看到像素点，而非默认渲染方式的无限精细

- 三维空间中的深度测试（ :meth:`~.Item.apply_depht_test` ）无效

总之，设置 ``render='pixel'`` ，即通过只能平移和旋转等简单操作，来换取极高的性能。
