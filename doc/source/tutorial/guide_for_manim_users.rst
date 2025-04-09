面向 Manim 用户的指南
==============================

JAnim 在使用上与 Manim 有很多相似之处，尤其是对于 Manim 的用户来说，上手使用 JAnim 会更容易。

下面是 Manim 和 JAnim 之间一些功能的对照表：

.. raw:: html

    <div class="mj-comparison-table">

.. list-table::
    :header-rows: 1

    *   -   功能
        -   Manim
        -   JAnim
        -   备注
    *   -   对象/物件
        -   ``Mobject``, ``VMobject``
        -   :class:`~.Item`, :class:`~.VItem`
        -
    *   -   前进一段时间
        -   ``self.wait(时长)``
        -   ``self.forward(时长)``
        -
    *   -   将物件添加到场景中
        -   ``self.add(xxx)``
        -   ``self.show(xxx)``
        -   也可以使用 ``xxx.show()``
    *   -   矩形
        -   ``Rectangle``
        -   :class:`~.Rect`
        -
    *   -   圆角矩形
        -   ``RoundedRectangle``
        -   :class:`~.RoundedRect`
        -
    *   -   包围矩形
        -   ``SurroundingRectangle``
        -   :class:`~.SurroundingRect`
        -
    *   -   设置 :class:`~.VItem` 描边粗细
        -   ``xxx.set_stroke(width=粗细)``
        -   ``xxx.radius.set(粗细半径)``
        -   二者粗细的含义不同，请自行尝试

.. raw:: html

    </div>

进一步的学习请阅读 :ref:`入门 <get_started>` 页面的内容

欢迎在该页面补充更多信息！
