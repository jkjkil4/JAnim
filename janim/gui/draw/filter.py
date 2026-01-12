import math


class OneEuroVec2:
    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

        self.p = None      # filtered position (x, y)
        self.v = 0.0       # filtered speed
        self.last_t = None

    @staticmethod
    def _alpha(cutoff: float, te: float) -> float:
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / te)

    def __call__(self, x: float, y: float, t: float):
        if self.last_t is None:
            self.last_t = t
            self.p = (x, y)
            return self.p

        te = t - self.last_t
        self.last_t = t
        if te <= 0.0:
            return self.p

        px, py = self.p
        dx = (x - px) / te
        dy = (y - py) / te
        speed = math.hypot(dx, dy)

        a_d = self._alpha(self.d_cutoff, te)
        self.v = a_d * speed + (1 - a_d) * self.v

        cutoff = self.min_cutoff + self.beta * self.v
        a = self._alpha(cutoff, te)

        self.p = (
            px + a * (x - px),
            py + a * (y - py),
        )
        return self.p

    def reset(self):
        self.p = None
        self.v = 0.0
        self.last_t = None
