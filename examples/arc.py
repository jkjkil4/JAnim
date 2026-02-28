from janim.imports import *

class ArcExample(Timeline):
    def construct(self):
        arc = Arc(start_angle=PI / 2, end_angle=PI / 2 + 2 * PI, radius=2)
        self.show(arc)
        self.play(arc.anim.radius.set(4))
        self.play(arc.anim.radius.set(8))
        self.play(arc.anim.radius.set(16))

