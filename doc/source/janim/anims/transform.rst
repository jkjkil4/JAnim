transform
=========

.. note::

    使用 :class:`~.Transform` 进行不同文字间的变换可能不会有足够好的效果，在使用时请多加斟酌

.. autoclass:: janim.anims.transform.Transform
    :show-inheritance:

.. janim-example:: TransformExample
    :media: ../../_static/videos/TransformExample.mp4

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

.. janim-example:: TransformInSegmentsExample
    :media: ../../_static/videos/TransformInSegmentsExample.mp4

    class TransformInSegmentsExample(Timeline):
        def construct(self):
            typ1 = Typst('sin x + cos x')
            typ2 = Typst('cos y + sin y')
            Group(typ1, typ2).points.scale(3)

            self.show(typ1)
            self.forward(0.5)
            self.play(TransformInSegments(typ1, [[0,3,4], [5,8,9]],
                                          typ2, [None, None],
                                          lag_ratio=0.5))
            self.forward(0.5)

.. autoclass:: janim.anims.transform.MethodTransform
    :show-inheritance:

.. janim-example:: MethodTransformExample
    :media: ../../_static/videos/MethodTransformExample.mp4

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
