from __future__ import annotations

from typing import Self

import numpy as np

import janim.utils.refresh as refresh
from janim.components.points import Cmpt_Points
from janim.constants import OUT
from janim.utils.space_ops import get_norm, get_unit_normal

# TODO: 注释


class Cmpt_VPoints(Cmpt_Points):
    def copy(self) -> Self:
        return super().copy()

    def __eq__(self, other: Cmpt_VPoints) -> bool:
        return super().__eq__(other)

    def get_anchors(self) -> np.ndarray:
        return self.get()[::2]

    def get_start_anchors(self) -> np.ndarray:
        return self.get()[0:-1:2]

    def get_end_anchors(self) -> np.ndarray:
        return self.get()[2::2]

    def get_handles(self) -> np.ndarray:
        return self.get()[1::2]

    @property
    @Cmpt_Points.set.self_refresh()
    @refresh.register
    def area_vector(self) -> np.ndarray:
        # Returns a vector whose length is the area bound by
        # the polygon formed by the anchor points, pointing
        # in a direction perpendicular to the polygon according
        # to the right hand rule.
        if not self.has():
            return np.zeros(3)

        p0 = self.get_anchors()
        p1 = np.roll(p0, -1, axis=0)

        # Each term goes through all edges [(x0, y0, z0), (x1, y1, z1)]
        sums = p0 + p1
        diffs = p1 - p0
        return 0.5 * np.array([
            (sums[:, 1] * diffs[:, 2]).sum(),  # Add up (y0 + y1)*(z1 - z0)
            (sums[:, 2] * diffs[:, 0]).sum(),  # Add up (z0 + z1)*(x1 - x0)
            (sums[:, 0] * diffs[:, 1]).sum(),  # Add up (x0 + x1)*(y1 - y0)
        ])

    @property
    @Cmpt_Points.set.self_refresh()
    @refresh.register
    def unit_normal(self) -> np.ndarray:
        if self.count() < 3:
            return OUT

        area_vect = self.area_vector
        area = get_norm(area_vect)
        if area > 0:
            return area_vect / area

        points = self.get()
        return get_unit_normal(
            points[1] - points[0],
            points[2] - points[1]
        )

    def get_closepath_flags(self) -> np.ndarray:
        result = np.full(self.count(), False)
        if len(result) == 0:
            return result

        points = self.get()

        start = points[0]
        start_idx = 0

        for i, (anchor1, handle, anchor2) in enumerate(
            zip(
                self.get_start_anchors(),
                self.get_handles(),
                self.get_end_anchors()
            )
        ):
            if np.all(anchor1 == handle):
                if np.all(anchor1 == start):
                    result[start_idx:i * 2 + 1] = True
                start = anchor2
                start_idx = i * 2 + 2

        last_idx = (len(points) - 1) // 2 * 2
        if np.all(points[last_idx] == start):
            result[start_idx:last_idx + 1] = True

        return result
