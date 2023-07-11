from janim import *

class DotCloudTest(Scene):
    def construct(self) -> None:
        dots = DotCloud([
            RIGHT * i + UP * j + OUT * k
            for i in range(4)
            for j in range(4)
            for k in range(4)
        ]).set_radius(0.2).set_color([GREEN_A, BLUE_B, YELLOW_B]).to_center()
        
        self.add(dots)

class VItemTest(Scene):
    def construct(self) -> None:
        m1 = VItem()
        m1.set_points_as_corners([ORIGIN, DOWN, DR, RIGHT]).close_path()

        self.add(m1)
        # print(m1.get_points(), *m1.get_subpaths(), sep='\n')

class GeometryTest(Scene):
    def construct(self) -> None:
        group = Group(
            Group(
                Arc(20 * DEGREES, 160 * DEGREES),
                Arc(40 * DEGREES, 230 * DEGREES)
            ).arrange(),
            Group(
                Circle(),
                Circle(radius=1.5),
                Ellipse()
            ).arrange(),
            Group(
                AnnularSector(),
                AnnularSector(0.5, 1.5, 60 * DEGREES, 60 * DEGREES),
                Sector(),
                Annulus()
            ).arrange()
        ).arrange(DOWN)

        self.add(group)

GeometryTest().run()
