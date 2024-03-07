# flake8: noqa
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


class SimpleCurveExample(Timeline):
    def construct(self) -> None:
        item1 = VItem(
            LEFT * 2, DR, UR * 3 + UP, RIGHT * 4, DR * 2, DOWN * 2, LEFT * 2,
            NAN_POINT,
            DL * 3, DL * 2, DOWN * 3, DL * 4, DL * 3,
        )
        item1.fill.set(alpha=0.5)
        item1.show()

        self.forward(0.5)
        self.play(item1.anim.color.set(BLUE))
        self.play(Rotate(item1, -90 * DEGREES))
        self.forward(0.5)

        item2 = VItem(LEFT, UP, RIGHT, DOWN, LEFT)
        item2.color.set(BLUE)
        item2.fill.set(alpha=0.2)

        state = self.camera.store_data()
        self.play(self.camera.anim.points.scale(0.5))
        self.play(self.camera.anim.become(state))

        self.play(
            Transform(item1, item2),
            duration=2
        )
        self.forward(1)


class TextExample(Timeline):
    def construct(self) -> None:
        txt = Text('Here is a text', font_size=64)
        desc = Group(
            Text('You can also apply <c BLUE>styles</c> to the text.', format=Text.Format.RichText),
            Text('You can also apply <c GREEN><fs 1.4>styles</fs></c> to the text.', format=Text.Format.RichText),
        )
        group = Group(txt, desc)
        group.points.arrange(DOWN, buff=MED_LARGE_BUFF)

        self.forward()
        self.play(Write(txt))
        self.play(FadeIn(desc[0], UP))
        self.play(Transform(desc[0], desc[1]))
        self.forward()


typst_doc = '''
JAnim provides #text(green)[`TypstDoc`] class to insert typst document.

Math expressions are also available.

$ A = pi r^2 $
$ "area" = pi dot "radius"^2 $
$ cal(A) :=
    { x in RR | x "is natural" } $
#let x = 5
$ #x < 17 $

The difference between #text(green)[`TypstDoc`] and #text(green)[`Typst`]:
- #text(green)[`TypstDoc`] automatically align to the top of view,
  so you can see the document from the start.
- The content of #text(green)[`Typst`] is wrapped by math environment
  and the item move to the center by default.
'''


class TypstExample(Timeline):
    def construct(self) -> None:
        doc = TypstDoc(typst_doc)
        typ = Typst('sum_(i=1)^n x_i')

        self.show(doc)
        self.forward()
        self.hide(doc)
        self.show(typ)
        self.forward()
