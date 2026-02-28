from janim.imports import *

class BubbleSort(Timeline):
    def construct(self):
        num = 100

        # define items
        heights = np.linspace(1.0, 6.0, num)
        w = 8.0 * 16.0 / 9.0 / num
        np.random.seed(123456)
        np.random.shuffle(heights)
        rects = [
            Rect(w, height,
                 fill_alpha=0.5)
            for height in heights
        ]

        group = Group(*rects)
        group.points.arrange(aligned_edge=DOWN, buff=0.00)

        # do animations
        self.show(group)

        for i in range(len(heights) - 1, 0, -1):
            for j in range(i):
                rect1, rect2 = rects[j], rects[j + 1]

                self.play(
                    rect1.anim.color.set(BLUE),
                    rect2.anim.color.set(BLUE),
                    duration=0.15
                )

                if heights[j] > heights[j + 1]:
                    x1 = rect1.points.box.x
                    x2 = rect2.points.box.x

                    self.play(
                        rect1.anim.points.set_x(x2),
                        rect2.anim.points.set_x(x1),
                        duration=0.15
                    )

                    heights[[j, j + 1]] = heights[[j + 1, j]]
                    rects[j], rects[j + 1] = rect2, rect1

                self.play(
                    rect1.anim.color.set(WHITE),
                    rect2.anim.color.set(WHITE),
                    duration=0.15
                )