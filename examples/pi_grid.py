from janim.imports import *

class AnimatingPiExample(Timeline):
    def construct(self):
        grid = Typst('pi') * 100
        grid.points.scale(2).arrange_in_grid(10, 10, buff=0.2)
        grid.show()

        self.play(grid.anim.points.shift(LEFT))
        self.play(grid(VItem).anim.color.set(YELLOW))
        self.forward()
        self.play(grid(VItem).anim.color.set(BLUE))
        self.forward()
        self.play(grid.anim.points.to_center().set_height(TAU - MED_SMALL_BUFF))
        self.forward()

        self.play(grid.anim.points.apply_complex_fn(np.exp), duration=5)
        self.forward()

        self.play(
            grid.anim.points.apply_point_fn(
                lambda p: [
                    p[0] + 0.5 * math.sin(p[1]),
                    p[1] + 0.5 * math.sin(p[0]),
                    p[2]
                ]
            ),
            duration=5
        )
        self.forward()