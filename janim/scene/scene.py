from __future__ import annotations
from janim.typing import Self

import itertools as it
import traceback
import inspect
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import (
    QMatrix4x4, QVector3D,
    QSurfaceFormat
)

from janim.constants import *
from janim.scene.loop_helper import LoopHelper
from janim.items.item import Item, UpdaterFn, Updater, NonParentGroup
from janim.utils.space_ops import get_unit_normal, get_norm
from janim.utils.functions import get_proportional_scale_size
from janim.config import get_cli, get_configuration
from janim.animation.animation import Animation
from janim.animation.composition import AnimationGroup

from janim.gl.render import RenderData

class Scene:
    anti_alias_width = 0.015
    background_color = None

    def __init__(self) -> None:
        cli = get_cli()
        conf = get_configuration()

        if self.background_color is None:
            self.background_color = conf['style']['background_color']
            
        self.write_to_file = cli.write_file or cli.transparent or cli.gif or cli.open
        self.start_at_line_number, self.end_at_line_number = self.get_start_and_end_line_number()
        
        if cli.frame_rate:
            self.frame_rate = int(cli.frame_rate)
        else:
            self.frame_rate = conf['frame_rate']
        
        self.camera = Camera()

        self.updaters: list[Updater] = []

        # relation
        self.items: list[Item] = []
        self.saved_state: dict[str, dict[str, list[Item]]] = {}
    
    def get_start_and_end_line_number(self) -> tuple[int | None, int | None]:
        stln = get_cli().start_at_line_number
        if stln is None:
            return None, None
        if ',' in stln:
            start, end = stln.split(',')
            return int(start), int(end)
        return int(stln), None

    #region 基本结构

    def __getitem__(self, value) -> Item | NonParentGroup:
        if isinstance(value, slice):
            return NonParentGroup(*self.items[value])
        return self.items[value]

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def add(self, *items: Item) -> Self:
        for item in items:
            if item in self:
                continue
            if item.parent is not None:
                item.parent.remove(item)
            self.items.append(item)
            item.parent = self
        return self
    
    def add_to_front(self, item: Item) -> Self:
        if item.parent is not None:
            item.parent.remove(item)
        self.add(item)
        return self
    
    def add_to_back(self, item: Item) -> Self:
        if item.parent is not None:
            item.parent.remove(item)
        self.items.insert(0, item)
        item.parent = self
        return self

    def remove(self, *items: Item) -> Self:
        for item in items:
            if item in self:
                item.parent = None
                self.items.remove(item)
                continue
            if item.parent is not None:
                item.parent.remove(item)
        return self
    
    def replace_subitem(self, item: Item, target: Item) -> Self:
        if item in self.items:
            item.parent = None
            self.items[self.items.index(item)] = target
            target.parent = self
        return self
    
    def clear(self) -> Self:
        self.remove(*self.items)
        return self
    
    def mark_needs_new_family(self) -> None:
        pass

    def mark_needs_new_family_with_helpers(self) -> None:
        pass
    
    def get_family(self) -> list[Item]:
        return list(it.chain(*(item.get_family() for item in self.items)))
    
    #endregion
    
    #region 基本操作

    def save_state(self, key: str = '') -> Self:
        self.saved_state[key] = {
            'items': self.items[:],
            'item_states': [item.copy() for item in self.items]
        }
        return self

    def restore(self, key: str = '') -> Self:
        if key not in self.saved_state:
            raise Exception("Trying to restore scene without having saved")
        saved_state = self.saved_state[key]
        items = saved_state['items']
        states = saved_state['item_states']
        for item, state in zip(items, states):
            item.become(state)
        self.items = items[:]
        return self

    #endregion

    #region 执行

    def run(self) -> None:
        app = QApplication.instance()
        if not app:
            app = QApplication()
        
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setSamples(4)
        QSurfaceFormat.setDefaultFormat(fmt)

        if self.write_to_file:
            from janim.gl.frame import Frame
            self.scene_writer = Frame(self)
        else:
            from janim.gui.MainWindow import MainWindow
            self.scene_writer = MainWindow(self)
            self.scene_writer.show()

        self.loop_helper = LoopHelper(self.frame_rate)

        try:
            self.construct()
            self.scene_writer.finish()
        except EndSceneEarlyException:
            pass
        except:
            traceback.print_exc()

        if not self.write_to_file and not self.scene_writer.is_closed:
            app.exec()
        

    def construct(self) -> None:
        pass

    def check_skipping(self) -> bool:
        if self.start_at_line_number is None and self.end_at_line_number is None:
            return False

        # 得到位于 construct 下的执行行数
        frame = inspect.currentframe()
        while True:
            frame = frame.f_back
            if frame is None:
                return False
            if frame.f_code.co_name == 'construct':
                break
        lineno = frame.f_lineno

        if self.end_at_line_number is not None and lineno > self.end_at_line_number:
            raise EndSceneEarlyException()
        
        if self.start_at_line_number is not None:
            return lineno < self.start_at_line_number
        return False

    def play(self, *anims: Animation, **kwargs) -> None:
        skipping = self.check_skipping()
        anim = AnimationGroup(*anims, **kwargs)
        anim.set_scene_instance(self)
        elapsed = 0
        def fn_progress(dt: float) -> None:
            nonlocal elapsed
            elapsed += dt
            anim.update(elapsed, dt)
            self.update_frame(dt)
            self.scene_writer.emit_frame()

        f_back = inspect.currentframe().f_back
        succ = self.loop_helper.exec(
            fn_progress, 
            anim.begin_time + anim.run_time,
            delay=not self.write_to_file and not skipping,
            desc=f'Scene.play() at {os.path.basename(f_back.f_code.co_filename)}:{f_back.f_lineno}'
        )
        if not succ or (not self.write_to_file and self.scene_writer.is_closed):
            raise EndSceneEarlyException()
        anim.finish_all()

    def wait(self, duration: float = DEFAULT_WAIT_TIME) -> None:
        skipping = self.check_skipping()
        def fn_progress(dt: float) -> None:
            self.update_frame(dt)
            self.scene_writer.emit_frame()

        f_back = inspect.currentframe().f_back
        succ = self.loop_helper.exec(
            fn_progress, 
            duration,
            delay=not self.write_to_file and not skipping,
            desc=f'Scene.wait() at {os.path.basename(f_back.f_code.co_filename)}:{f_back.f_lineno}'
        )
        if not succ or (not self.write_to_file and self.scene_writer.is_closed):
            raise EndSceneEarlyException()
    
    def update_frame(self, dt: float) -> None:
        for updater in self.updaters:
            updater.do(dt)
        for item in self.items:
            item.update(dt)

    def add_updater(self, fn: UpdaterFn) -> Updater:
        for updater in self.updaters:
            if fn is updater.fn:
                return updater
        updater = Updater(self, fn)
        self.updaters.append(updater)
        return updater
    
    def remove_updater(self, updater_or_fn: Updater | UpdaterFn) -> Self:
        for updater in self.updaters:
            if updater is updater_or_fn or updater.fn is updater_or_fn:
                self.updaters.remove(updater)
                break
        return self

    #endregion

    #region 渲染

    def render(self) -> None:
        data = RenderData(
            self.anti_alias_width,
            self.camera.wnd_shape,
            self.camera.compute_view_matrix(),
            self.camera.compute_proj_matrix(),
            self.camera.compute_wnd_matrix(),
        )

        for item in self:
            item.render(data)

    #endregion

class Camera(Item):
    frame_shape = (FRAME_WIDTH, FRAME_HEIGHT)
    wnd_shape = (1920, 1080)
    center_point = ORIGIN

    def __init__(self) -> None:
        super().__init__()

        self.reset()
    
    def reset(self):
        self.fov = 45
        self.set_points([ORIGIN, LEFT_SIDE, RIGHT_SIDE, BOTTOM, TOP])
        return self

    def get_horizontal_vect(self) -> np.ndarray:
        return self.points[2] - self.points[1]

    def get_horizontal_dist(self) -> float:
        return get_norm(self.get_horizontal_vect())
    
    def get_vertical_vect(self) -> np.ndarray:
        return self.points[4] - self.points[3]
    
    def get_vertical_dist(self) -> float:
        return get_norm(self.get_vertical_vect())

    def compute_view_matrix(self) -> QMatrix4x4:
        center = self.points[0]
        hor = self.get_horizontal_vect()
        ver = self.get_vertical_vect()
        normal = get_unit_normal(hor, ver)
        distance = get_norm(ver) / 2 / np.tan(np.deg2rad(self.fov / 2))

        view = QMatrix4x4()
        view.setToIdentity()
        view.lookAt(QVector3D(*(center + normal * distance)), QVector3D(*center), QVector3D(*(ver)))

        return view

    def compute_proj_matrix(self) -> QMatrix4x4:
        projection = QMatrix4x4()
        projection.setToIdentity()
        projection.scale(FRAME_X_RADIUS, FRAME_Y_RADIUS)
        projection.perspective(self.fov, self.frame_shape[0] / self.frame_shape[1], 0.1, 100)

        return projection
    
    def compute_wnd_matrix(self) -> QMatrix4x4:
        window = QMatrix4x4()
        window.setToIdentity()
        res_width, res_height = get_proportional_scale_size(*self.frame_shape, *self.wnd_shape)
        window.scale(res_width / self.wnd_shape[0] / FRAME_X_RADIUS, res_height / self.wnd_shape[1] / FRAME_Y_RADIUS)

        return window


class EndSceneEarlyException(Exception):
    pass
