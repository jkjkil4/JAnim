from __future__ import annotations

from typing import Generator, Iterable, Self

import numpy as np

import janim.utils.refresh as refresh
from janim.components.points import Cmpt_Points
from janim.constants import OUT
from janim.logger import log
from janim.typing import VectArray
from janim.utils.bezier import partial_quadratic_bezier_points
from janim.utils.data import AlignedData
from janim.utils.space_ops import get_norm, get_unit_normal

# TODO: 注释
# TODO: 注释：关于子路径结束是如何判定的


class Cmpt_VPoints[ItemT](Cmpt_Points[ItemT]):
    def copy(self) -> Self:
        return super().copy()

    def become(self, other: Cmpt_VPoints) -> Self:
        super().become(other)
        return self

    def __eq__(self, other: Cmpt_VPoints) -> bool:
        return super().__eq__(other)

    def set(self, points: VectArray) -> Self:
        if len(points) != 0 and len(points) % 2 == 0:
            points = points[:-1]
            log.warning(f'设置的点数量为 {len(points)}，不是奇数，最后一个点被忽略')
        super().set(points)

    # region align

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_VPoints, cmpt2: Cmpt_VPoints):
        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()

        if cmpt1_copy == cmpt2_copy:
            return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

        if not cmpt1_copy.has():
            cmpt1_copy.set([cmpt2.box.center])
        if not cmpt2_copy.has():
            cmpt2_copy.set([cmpt1.box.center])

        subpaths1 = cmpt1_copy.get_subpaths()
        subpaths2 = cmpt2_copy.get_subpaths()
        for subpaths in [subpaths1, subpaths2]:
            subpaths.sort(
                key=lambda sp: sum(
                    get_norm(p2 - p1)
                    for p1, p2 in zip(sp, sp[1:])
                ),
                reverse=True
            )
        n_subpaths = max(len(subpaths1), len(subpaths2))

        # 构建新的子路径
        new_subpaths1 = []
        new_subpaths2 = []

        def get_nth_subpath(path_list: list[np.ndarray], n: int) -> np.ndarray:
            if n >= len(path_list):
                return np.vstack([path_list[0][:-1], path_list[0][::-1]])
            return path_list[n]

        for n in range(n_subpaths):
            sp1 = get_nth_subpath(subpaths1, n)
            sp2 = get_nth_subpath(subpaths2, n)
            diff1 = max(0, (len(sp2) - len(sp1)) // 2)
            diff2 = max(0, (len(sp1) - len(sp2)) // 2)
            sp1 = cls.insert_n_curves_to_point_list(diff1, sp1)
            sp2 = cls.insert_n_curves_to_point_list(diff2, sp2)
            if n > 0:
                # Add intermediate anchor to mark path end
                new_subpaths1.append(new_subpaths1[-1][-1])
                new_subpaths2.append(new_subpaths2[-1][-1])
            new_subpaths1.append(sp1)
            new_subpaths2.append(sp2)

        cmpt1_copy.set(np.vstack(new_subpaths1))
        cmpt2_copy.set(np.vstack(new_subpaths2))

        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

    @staticmethod
    def insert_n_curves_to_point_list(n: int, points: VectArray) -> np.ndarray:
        if len(points) == 1:
            return np.repeat(points, 2 * n + 1, 0)

        bezier_tuples = list(Cmpt_VPoints.get_bezier_tuples_from_points(points))
        norms = [
            0 if (tup[0] == tup[1]).all() else get_norm(tup[2] - tup[0])
            for tup in bezier_tuples
        ]
        # Calculate insertions per curve (ipc)
        ipc = np.zeros(len(bezier_tuples), dtype=int)
        for _ in range(n):
            index = np.argmax(norms)
            ipc[index] += 1
            norms[index] *= ipc[index] / (ipc[index] + 1)

        new_points = [points[0]]
        for tup, n_inserts in zip(bezier_tuples, ipc):
            # What was once a single quadratic curve defined
            # by "tup" will now be broken into n_inserts + 1
            # smaller quadratic curves
            alphas = np.linspace(0, 1, n_inserts + 2)
            for a1, a2 in zip(alphas, alphas[1:]):
                new_points.extend(partial_quadratic_bezier_points(tup, a1, a2)[1:])

        return np.vstack(new_points)

    # endregion

    # region anchors and handles

    def get_anchors(self) -> np.ndarray:
        return self.get()[::2]

    def get_handles(self) -> np.ndarray:
        return self.get()[1::2]

    @staticmethod
    def get_bezier_tuples_from_points(points: VectArray) -> Iterable[np.ndarray]:
        n_curves = max(0, len(points) - 1) // 2
        return (points[2 * i: 2 * i + 3] for i in range(n_curves))

    def curves_count(self) -> int:
        return max(0, self.count() - 1) // 2

    # endregion

    # region unit_normal

    @property
    @Cmpt_Points.set.self_refresh()
    @refresh.register
    def area_vector(self) -> np.ndarray:
        '''
        一个向量，其长度为锚点形成的多边形所围成的面积，根据右手定则指向垂直于该多边形的方向
        '''
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

    # endregion

    # region subpaths

    def walk_subpath_end_indices(self) -> Generator[int, None, None]:
        points = self.get()
        a0, h = points[0:-1:2], points[1::2]
        yield from np.where((a0 == h).all(1))[0] * 2
        yield len(points) - 1

    def get_subpath_end_indices(self) -> list[int]:
        return list(self.walk_subpath_end_indices())

    def get_closepath_flags(self) -> np.ndarray:
        result = np.full(self.count(), False)
        if len(result) == 0:
            return result

        points = self.get()

        start_idx = 0
        for end_idx in self.walk_subpath_end_indices():
            if (points[end_idx] == points[start_idx]).all():
                result[start_idx: end_idx + 1] = True
            start_idx = end_idx + 2

        return result

    @staticmethod
    def get_parts_by_end_indices(array: np.ndarray, end_indices: np.ndarray) -> list[np.ndarray]:
        if len(array) == 0:
            return []
        start_indices = [0, *(end_indices[:-1] + 2)]
        return [array[i1: i2 + 1] for i1, i2 in zip(start_indices, end_indices)]

    def get_subpaths(self) -> list[np.ndarray]:
        return self.get_parts_by_end_indices(self.get(), np.array(self.get_subpath_end_indices()))

    # endregion
