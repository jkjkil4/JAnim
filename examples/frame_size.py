from janim.imports import *

class FrameSizeExample(Timeline):
    def construct(self):
        square = Square(2)
        self.show(square)

        for i in range(1, 8):
            square = Square(i * 2)
            self.play(square.anim.become(square))


