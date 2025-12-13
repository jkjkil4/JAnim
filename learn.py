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
#  janim run learn.py HelloJAnimExample