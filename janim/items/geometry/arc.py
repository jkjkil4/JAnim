from janim.typing import Self

from janim.constants import *
from janim.items.item import Item, Point
from janim.items.vitem import VItem
from janim.utils.space_ops import (
    angle_of_vector, get_norm,
    angle_between_vectors
)

DEFAULT_DOT_RADIUS = 0.08
DEFAULT_SMALL_DOT_RADIUS = 0.04

class Arc(VItem):
    '''
    圆弧

    传入 `start_angle` 指定起始的角度，`angle` 表示圆心角
    '''
    def __init__(
        self,
        start_angle: float = 0,
        angle: float = TAU / 4,
        radius: float = 1.0,
        *,
        n_components: int = 8,
        arc_center: np.ndarray = ORIGIN,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.set_points(
            Arc.create_quadratic_bezier_points(
                angle=angle,
                start_angle=start_angle,
                n_components=n_components
            ) * radius
        )
        self.shift(arc_center)

        self.center_point = Point(arc_center)
        self.add(self.center_point, is_helper=True)

    @staticmethod
    def create_quadratic_bezier_points(
        angle: float,
        start_angle: float = 0,
        n_components: int = 8
    ) -> np.ndarray:
        '''得到使用二次贝塞尔曲线模拟的圆弧'''
        samples = np.array([
            [np.cos(a), np.sin(a), 0]
            for a in np.linspace(
                start_angle,
                start_angle + angle,
                2 * n_components + 1,
            )
        ])
        theta = angle / n_components
        samples[1::2] /= np.cos(theta / 2)

        points = np.zeros((3 * n_components, 3))
        points[0::3] = samples[0:-1:2]
        points[1::3] = samples[1::2]
        points[2::3] = samples[2::2]
        return points

    def get_arc_center(self) -> np.ndarray:
        '''获取圆弧圆心'''
        return self.center_point.get_pos()
    
    def get_arc_length(self) -> float:
        '''获取圆弧长度'''
        center = self.get_arc_center()
        p0 = self.get_start()
        p1 = self.pfp(0.5)
        vc0 = p0 - center
        vc1 = p1 - center

        return 2 * get_norm(vc0) * angle_between_vectors(vc0, vc1)

    def get_start_angle(self) -> float:
        '''获取起始角度'''
        angle = angle_of_vector(self.get_start() - self.get_arc_center())
        return angle % TAU

    def get_stop_angle(self) -> float:
        '''获取终止角度'''
        angle = angle_of_vector(self.get_end() - self.get_arc_center())
        return angle % TAU

    def move_arc_center_to(self, point: np.ndarray) -> Self:
        '''将圆弧圆心移动到指定的位置'''
        self.shift(point - self.get_arc_center())
        return self

class ArcBetweenPoints(Arc):
    '''
    两点之间的圆弧

    - 传入 `start`, `end` 表示起点终点，`angle` 表示圆心角
    - 其余参数同 `Arc`
    '''
    def __init__(
        self,
        start: np.ndarray,
        end: np.ndarray,
        angle: float = TAU / 4,
        **kwargs
    ) -> None:
        super().__init__(angle=angle, **kwargs)
        if angle == 0:
            self.set_points_as_corners([LEFT, RIGHT])
        self.put_start_and_end_on(start, end)

class Circle(Arc):
    '''
    圆

    - 参数同 `Arc`
    - 半径传入 `radius` 指定
    '''
    def __init__(self, **kwargs) -> None:
        super().__init__(0, TAU, **kwargs)

    def surround(
        self,
        item: Item,
        dim_to_match: int = 0,
        stretch: bool = False,
        buff: float = MED_SMALL_BUFF
    ) -> Self:
        # Ignores dim_to_match and stretch; result will always be a circle
        # TODO: [L] Perhaps create an ellipse class to handle singele-dimension stretching
        self.replace(item, dim_to_match, stretch)
        self.stretch((self.get_width() + 2 * buff) / self.get_width(), 0)
        self.stretch((self.get_height() + 2 * buff) / self.get_height(), 1)
        return self

    def point_at_angle(self, angle: float) -> np.ndarray:
        start_angle = self.get_start_angle()
        return self.point_from_proportion(
            (angle - start_angle) / TAU
        )

    def get_radius(self) -> float:
        return get_norm(self.get_start() - self.get_center())
    

class Dot(Circle):
    '''
    点（半径默认为0.08）
    '''
    def __init__(
        self,
        point: np.ndarray = ORIGIN,
        *,
        radius: float = DEFAULT_DOT_RADIUS,
        stroke_width: float = 0,
        fill_opacity: float = 1.0,
        **kwargs
    ) -> None:
        super().__init__(
            arc_center=point,
            radius=radius,
            stroke_width=stroke_width,
            fill_opacity=fill_opacity,
            **kwargs
        )

class SmallDot(Dot):
    '''
    小点（半径默认为0.04）
    '''
    def __init__(self, *, radius: float = DEFAULT_SMALL_DOT_RADIUS, **kwargs) -> None:
        super().__init__(radius=radius, **kwargs)


class Ellipse(Circle):
    '''
    椭圆
    '''
    def __init__(
        self,
        width: float = 2,
        height: float = 1,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.set_size(width, height)

class AnnularSector(VItem):
    '''
    扇环

    - `inner_radius`: 内圆半径
    - `outer_radius`: 外圆半径
    - `start_angle`: 起始角度
    - `angle`: 圆心角
    - `arc_center`: 圆弧的中心
    '''
    def __init__(
        self,
        inner_radius: float = 0.5,
        outer_radius: float = 1,
        start_angle: float = 0,
        angle: float = TAU / 4,
        *,
        arc_center: np.ndarray = ORIGIN,
        n_components: int = 8,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        unit = Arc.create_quadratic_bezier_points(
            angle=angle,
            start_angle=start_angle,
            n_components=n_components
        )

        inner_arc, outer_arc = (
            unit * radius + arc_center
            for radius in (inner_radius, outer_radius)
        )
        inner_arc = inner_arc[::-1]
        self.append_points(outer_arc)
        self.add_line_to(inner_arc[0])
        self.append_points(inner_arc)
        self.add_line_to(outer_arc[0])

        self.center_point = Point(arc_center)
        self.add(self.center_point, is_helper=True)

    def get_arc_center(self) -> np.ndarray:
        return self.center_point.get_pos()

    def move_arc_center_to(self, point: np.ndarray) -> Self:
        self.shift(point - self.get_arc_center())
        return self

class Sector(Arc):
    '''
    扇形

    传入参数请参考 `Arc`
    '''
    def __init__(self, *, arc_center: np.ndarray = ORIGIN, **kwargs) -> None:
        super().__init__(arc_center=arc_center, **kwargs)

        self.add_points_as_corners([arc_center, self.get_points()[0]])

class Annulus(VItem):
    '''
    圆环

    - `inner_radius`: 内圆半径
    - `outer_radius`: 外圆半径
    - `arc_center`: 圆弧的中心
    '''
    def __init__(
        self,
        outer_radius: float = 1,
        inner_radius: float = 0.5,
        *,
        arc_center: np.ndarray = ORIGIN,
        n_components: int = 8,
        fill_opacity: float = 0.5,
        **kwargs
    ) -> None:
        super().__init__(fill_opacity=fill_opacity, **kwargs)

        unit = Arc.create_quadratic_bezier_points(
            TAU, 0,
            n_components
        )
        
        inner, outer = (
            unit * radius + arc_center
            for radius in (inner_radius, outer_radius)
        )
        outer = outer[::-1]
        self.append_points(outer)
        self.append_points(inner)

