transform
=========

.. note::

    使用 :class:`~.Transform` 进行不同文字间的变换可能不会有足够好的效果，在使用时请多加斟酌

.. autoclass:: janim.anims.transform.Transform
    :show-inheritance:

.. janim-example:: TransformExample
    :media: ../../_static/videos/TransformExample.mp4

    from janim.imports import *

    class TransformExample(Timeline):
        def construct(self):
            A = Text('Text-A', font_size=72)
            B = Text('Text-B', font_size=72)
            C = Text('C-Text', font_size=72)

            A.show()
            self.forward()
            self.play(Transform(A, B))
            self.forward()
            self.play(Transform(B, C))
            self.forward()

.. autoclass:: janim.anims.transform.TransformInSegments
    :show-inheritance:

**基本用法**

.. code-block:: python

    TransformInSegments(a, [[0,3], [5,7]],
                        b, [[1,3], [5,7]])

相当于

.. code-block:: python

    AnimGroup(Transform(a[0:3], b[1:3]),
              Transform(a[5:7], b[5:7]))

**省略变换目标的切片**

使用 ``...`` 表示与变换来源的切片相同

.. code-block:: python

    TransformInSegments(a, [[0,3], [5,7]],
                        b, ...)

相当于

.. code-block:: python

    TransformInSegments(a, [[0,3], [5,7]],
                        b, [[0,3], [5,7]])

**连续切片**

.. code-block:: python

    TransformInSegments(a, [[0,3], [5,7,9]],
                        b, [[1,3], [4,7], [10,14]])

相当于

.. code-block:: python

    TransformInSegments(a, [[0,3], [5,7], [7,9]],
                        b, [[1,3], [4,7], [10,14]])

**切片简写**

如果总共只有一个切片，可以省略一层嵌套

.. code-block:: python

    TransformInSegments(a, [0, 4, 6, 8],
                        b, ...)

相当于

.. code-block:: python

    TransformInSegments(a, [[0, 4, 6, 8]],
                        b, ...)

**连续切片倒序**

倒过来写即可使切片倒序

.. code-block:: python

    TransformInSegments(a, [8, 6, 4, 0],
                        b, ...)

相当于

.. code-block:: python

    TransformInSegments(a, [[6,8], [4,6], [0,4]],
                        b, ...)

请留意 Python 切片中左闭右开的原则，对于倒序序列 ``[8, 6, 4, 0]`` 来说则是左开右闭

.. janim-example:: TransformInSegmentsExample
    :media: ../../_static/videos/TransformInSegmentsExample.mp4

    from janim.imports import *

    class TransformInSegmentsExample(Timeline):
        def construct(self):
            typ1 = Typst('sin x + cos x')
            typ2 = Typst('cos y + sin y')
            typ2.match_pattern(typ1, '+')
            Group(typ1, typ2).points.scale(3)

            self.show(typ1)
            self.forward(0.5)
            self.play(TransformInSegments(typ1, [[0,3,4], [5,8,9]],
                                          typ2, ...,
                                          lag_ratio=0.5))
            self.forward(0.5)

.. autoclass:: janim.anims.transform.MethodTransform
    :show-inheritance:

.. janim-example:: MethodTransformExample
    :media: ../../_static/videos/MethodTransformExample.mp4

    from janim.imports import *

    class MethodTransformExample(Timeline):
        def construct(self):
            A = Text("Text-A")
            A.points.to_border(LEFT)

            A.show()
            self.forward()
            self.play(
                A.anim.points.scale(3).shift(RIGHT * 7 + UP * 2)
            )
            self.play(
                A.anim.color.set(BLUE)
            )
            self.forward()

.. autoclass:: janim.anims.transform.TransformMatchingShapes
    :show-inheritance:

.. janim-example:: TransformMatchingShapesExample
    :media: ../../_static/videos/TransformMatchingShapesExample.mp4

    class TransformMatchingShapesExample(Timeline):
        def construct(self):
            a = Text("the morse code", font_size=48).show()
            b = Text("here come dots", font_size=48)

            self.forward()
            self.play(TransformMatchingShapes(a, b, path_arc=PI/2))
            self.forward()
            self.play(TransformMatchingShapes(b, a, path_arc=PI/2))
            self.forward()
