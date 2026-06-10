from __future__ import annotations

import gc
import inspect
import itertools as it
import math
import os
import time
import traceback
import types
from abc import abstractmethod
from bisect import bisect
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Literal, Self, overload

import moderngl as mgl
import numpy as np
from PIL import Image

from janim.anims_core.animation import Animation
from janim.anims_core.time import FOREVER, TimeChunks, TimeRange
from janim.camera.camera import Camera
from janim.camera.camera_info import CameraInfo
from janim.constants import DEFAULT_DURATION
from janim.exception import TimelineLookupError
from janim.items.item import Item
from janim.items.points import Point
from janim.locale import get_translator
from janim.logger import log
from janim.render.base import RenderData, Renderer, apply_blend_flags, create_context_430_or_330
from janim.render.collection import RenderCollection
from janim.render.framebuffer import FrameBuffer
from janim.render.uniform import uniforms
from janim.timeline.core import ItemAppearance, RenderGroupReturn, TimelineCore
from janim.timeline.misc import AudiosAndSubtitlesMixin, DebugMixin
from janim.timeline.pause_points import PausePointsMixin
from janim.utils.config import Config, ConfigGetter, config_ctx_var
from janim.utils.data import ContextSetter
from janim.utils.iterables import resize_preserving_order
from janim.utils.space_ops import normalize

_ = get_translator('janim.timeline.timeline')


class Timeline(PausePointsMixin, AudiosAndSubtitlesMixin, DebugMixin, TimelineCore):
    """
    继承该类并实现 :meth:`construct` 方法，以实现动画的构建逻辑

    调用 :meth:`build` 可以得到构建完成的 :class:`Timeline` 对象

    -----

    该类由若干基类实现功能，你可按照以下的分类跳转以参考对应的文档：

    -   核心功能： :class:`~.TimelineCore`

    -   “暂停点”功能： :class:`~.PausePointsMixin`

    -   对于音频与字幕，可参考：

        -   音频功能： :class:`~.AudiosMixin`

        -   字幕功能： :class:`~.SubtitlesMixin`

        -   对二者的结合： :class:`~.AudiosAndSubtitlesMixin`

    -   特殊的调试功能（但不太完善，慎用）： :class:`~.DebugMixin`

    -----
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._config_context: list[Config] | None = None

        self.gui_command: Timeline.GuiCommand | None = None

    @abstractmethod
    def construct(self) -> None:
        """
        继承该方法以实现动画的构建逻辑
        """
        pass  # pragma: no cover

    build_indent_ctx: ContextVar[int] = ContextVar('Timeline.build_indent_ctx')

    def build(self, *, quiet=False, hide_subtitles=False, show_debug_notice=False) -> BuiltTimeline:
        """
        构建动画并返回
        """
        indent = self.build_indent_ctx.get(-2) + 2
        indent_str = '  ' * indent
        with (
            self.config_context(),
            ContextSetter(self.ctx_var, self),
            ContextSetter(self.build_indent_ctx, indent),
        ):
            self.camera = Camera()
            self.track(self.camera)

            self.light_source = Point([-9, -7, 10])
            self.track(self.light_source)

            self.hide_subtitles = hide_subtitles
            self.show_debug_notice = show_debug_notice

            if not quiet:  # pragma: no cover
                log.info(indent_str + _('Building "{name}"').format(name=self.__class__.__name__))
                start_time = time.time()

            self._build_frame = inspect.currentframe()

            # 在 build 期间关闭 gc，这样只有重新 enable 之后的一次大 gc，这样可以提升效率
            gc_enabled = gc.isenabled()
            gc.disable()

            try:
                self.construct()
            except Timeline.GuiCommandInterrupt as e:
                self.gui_command = e.command

                # 使用 GUI 命令的时候，额外产生一点时间，避免最后一帧的效果不可预览的问题
                self.forward(DEFAULT_DURATION, _record_lineno=False)

                if not quiet:  # pragma: no cover
                    log.info(
                        indent_str
                        + (
                            _(
                                'Due to the use of a GUI command, '
                                '"{name}" automatically generated an additional duration of {duration}s'
                            ).format(
                                name=self.__class__.__name__,
                                duration=DEFAULT_DURATION,
                            )
                        )
                    )
            finally:
                self._build_frame = None
                if gc_enabled:
                    gc.enable()

            if self.current_time == 0:
                # 使得没有任何前进时，产生一点时间，避免除零以及其它问题
                self.forward(DEFAULT_DURATION, _record_lineno=False)

                if not quiet:  # pragma: no cover
                    log.info(
                        indent_str
                        + (
                            _(
                                '"{name}" did not produce a duration after construction, '
                                'automatically generated a duration of {duration}s'
                            ).format(
                                name=self.__class__.__name__,
                                duration=DEFAULT_DURATION,
                            )
                        )
                    )

            for appr in self.item_appearances.values():
                appr.stack.clear_cache()  # TODO: 检查这句是否有必要，并说明原因

            built = BuiltTimeline(self)

            if not quiet:  # pragma: no cover
                elapsed = time.time() - start_time  # type: ignore
                log.info(
                    indent_str
                    + (
                        _('Finished building "{name}" in {elapsed:.2f} s').format(
                            name=self.__class__.__name__,
                            elapsed=elapsed,
                        )
                    )
                )

        return built

    # region config

    CONFIG: Config | None = None
    """
    在子类中定义该变量可以起到设置配置的作用，例如：

    .. code-block::

        class Example(Timeline):
            CONFIG = Config(
                font=['Consolas', 'LXGW WenKai Lite']
            )

            def construct(self) -> None:
                ...

    关于可使用的配置，另见 :class:`~.Config`
    """

    @contextmanager
    def config_context(self):
        """
        在 :meth:`build` 方法中会发生第一次 ``with`` 调用，
        将当前的 ``config_ctx_var`` 上下文，与自己及各个父类的 :py:obj:`CONFIG` ，
        合并为该 Timeline 对象的 ``self._config_context``

        如果是之后的 ``with`` 调用，则会让内部代码块恢复 ``self._config_context`` 的状态，
        用于保证在相关上下文中的一致性
        """
        if self._config_context is None:
            mro_configs: list[Config] = []

            for sup in self.__class__.mro():
                config: Config | None = getattr(sup, 'CONFIG', None)
                if config is None or config in mro_configs:
                    continue
                mro_configs.append(config)

            self._config_context = [*config_ctx_var.get(), *reversed(mro_configs)]

            # 用于 `BuiltTimeline.cfg`
            self._config_getter = ConfigGetter(self._config_context)

        token = config_ctx_var.set(self._config_context)
        try:
            yield
        finally:
            config_ctx_var.reset(token)

    # endregion

    # region Timeline context

    ctx_var: ContextVar[Timeline | None] = ContextVar('Timeline.ctx_var')

    @overload
    @staticmethod
    def get_context(raise_exc: Literal[True] = True) -> Timeline: ...
    @overload
    @staticmethod
    def get_context(raise_exc: Literal[False]) -> Timeline | None: ...

    @staticmethod
    def get_context(raise_exc=True) -> Timeline | None:
        """
        调用该方法可以得到当前正在构建的 :class:`Timeline` 对象

        默认情况下，在 :meth:`construct` 方法外调用时，会抛出 :class:`~.TimelineLookupError` 错误；
        可以使用 ``raise_exc=False`` 禁用，在同样的情况下会返回 ``None`` 而非抛出错误

        :param raise_exc: 在不可用时，是否抛出错误
        """
        obj = Timeline.ctx_var.get(None)
        if obj is None and raise_exc:
            f_back: types.FrameType = inspect.currentframe().f_back  # type: ignore
            raise TimelineLookupError(
                _('{name} cannot be used outside of Timeline.construct').format(
                    name=f_back.f_code.co_qualname
                )
            )
        return obj

    # endregion

    # region GUI command

    class GuiCommand:
        def __init__(self, global_t: float, text: str, frame: types.FrameType):
            try:
                idx = text.index(':')
            except ValueError:
                idx = len(text)

            self.global_t = global_t
            self.text = text
            self.name = text[:idx].strip()
            self.body = text[idx + 1 :].strip()
            self.filepath = frame.f_code.co_filename
            self.lineno = frame.f_lineno
            self.locals = frame.f_locals

    class GuiCommandInterrupt(Exception):
        def __init__(self, command: Timeline.GuiCommand):
            super().__init__()
            self.command = command

    def __call__(self, command_text: str) -> None:
        command = Timeline.GuiCommand(
            self.current_time,
            command_text,
            inspect.currentframe().f_back,  # type: ignore
        )
        raise Timeline.GuiCommandInterrupt(command)

    # endregion


class BuiltTimeline:
    """
    运行 :meth:`Timeline.build` 后返回的实例
    """

    def __init__(self, timeline: Timeline):
        self.timeline = timeline
        self.duration = timeline.time_aligner.align_and_record(timeline.current_time)

        self.visible_item_segments = TimeChunks(
            ((item, appr) for item, appr in timeline.item_appearances.items()),
            lambda x: (
                TimeRange(*range) if len(range) == 2 else TimeRange(*range, self.duration + 1)
                for range in it.batched(x[1].visibility, 2)
            ),
        )
        self.visible_render_group_segments = TimeChunks(
            self.timeline.extra_render_groups,
            lambda x: (
                x.t_range
                if x.t_range.end is not FOREVER
                else TimeRange(x.t_range.at, self.duration + 1)
            ),
        )

        self._time: float = 0

        self.capture_ctx: mgl.Context | None = None
        self.capture_framebuffer: FrameBuffer | None = None

    @property
    def cfg(self) -> Config | ConfigGetter:
        """
        可以使用该方法获取 Timeline 构建时的上下文中的配置

        可用于在简单场景中避免使用 :meth:`config_context` ，例如：

        .. code-block:: python

            built.cfg.preview_fps
        """
        return self.timeline._config_getter

    def get_audio_samples_of_frame(
        self, fps: float, framerate: int, frame: int, *, count: int = 1
    ) -> np.ndarray:
        """
        提取特定帧的音频流
        """
        begin = frame / fps
        end = (frame + count) / fps
        channels = self.cfg.audio_channels

        output_sample_count = math.floor(end * framerate) - math.floor(begin * framerate)
        result = np.zeros((output_sample_count, channels), dtype=np.int16)

        # 合并自身的 audio
        for info in self.timeline.audio_infos:
            if end < info.range.at or begin > info.range.end:
                continue

            audio = info.audio

            frame_begin = int((begin - info.range.at + info.clip_range.at) * audio.framerate)
            frame_end = int((end - info.range.at + info.clip_range.at) * audio.framerate)

            clip_begin = max(0, int(audio.framerate * info.clip_range.at))
            clip_end = min(audio.sample_count(), int(audio.framerate * info.clip_range.end))

            left_blank = max(0, clip_begin - frame_begin)
            right_blank = max(0, frame_end - clip_end)

            data = audio._samples.data[max(clip_begin, frame_begin) : min(clip_end, frame_end)]

            if left_blank != 0 or right_blank != 0:
                # channels = data.shape[1]
                data = np.concatenate(
                    [
                        np.zeros((left_blank, channels), dtype=np.int16),
                        data,
                        np.zeros((right_blank, channels), dtype=np.int16),
                    ]
                )

            result += resize_preserving_order(data, output_sample_count)

        # 合并子 Timeline 的 audio
        for item in self.timeline.subtimeline_items:
            built = item._built
            frame_offset = int(item.at * fps)

            data = built.get_audio_samples_of_frame(
                fps, framerate, frame - frame_offset, count=count
            )
            result += resize_preserving_order(data, output_sample_count)

        return result

    def current_camera_info(self, *, as_time: float | None = None) -> CameraInfo:
        """
        得到当前的 :class:`~.CameraInfo` 信息

        这里“当前”的含义是，上次调用 :meth:`render_all` 的 ``global_t`` 时刻；或者也可以传入 ``as_time`` 指定
        """
        if as_time is None:
            as_time = self._time
        return self.timeline.compute_item(self.timeline.camera, as_time, True).points.info

    def render_all(
        self,
        ctx: mgl.Context,
        global_t: float,
        *,
        camera: Camera | None = None,
    ) -> bool:
        """
        渲染所有可见物件
        """
        timeline = self.timeline
        global_t = timeline.time_aligner.align(global_t)
        # 使得最后一帧采用略提早一点点的时间渲染，使得一些结束在结尾的动画不突变
        if global_t == self.duration:
            global_t -= 1e-4
        self._time = global_t

        try:
            # 有必要在计算 camera 和 light_source 之前设置这些 context
            # 因为用户有可能给 camera 或 light_source 使用 updater，updater 需要这些信息
            with (
                ContextSetter(Animation.global_t_ctx, global_t),
                ContextSetter(Timeline.ctx_var, self.timeline),
                self.timeline.config_context(),
            ):
                # 计算 camera 和 light_source
                if camera is None:
                    camera = timeline.compute_item(timeline.camera, global_t, True)
                camera_info = camera.points.info
                light_source = timeline.compute_item(timeline.light_source, global_t, True)
                anti_alias_radius = self.cfg.anti_alias_width / 2 * camera_info.scaled_factor

                # 用于渲染的基础信息
                # - 会提供给 _uniforms_data 以设置全局 shader uniform
                # - 会设置到 Renderer.data_ctx 使得在渲染器中可以访问到这些信息
                render_data = RenderData(
                    ctx=ctx,
                    camera_info=camera_info,
                    light_source_location=light_source.location,
                    anti_alias_radius=anti_alias_radius,
                )

                with (
                    self._uniforms_context(render_data),
                    ContextSetter(Renderer.data_ctx, render_data),
                ):
                    # 得到渲染集合
                    collection = self._get_render_collection(global_t)

                    # 进行渲染
                    collection.render()

        except Exception:
            traceback.print_exc()
            return False

        return True

    def _uniforms_context(self, data: RenderData):
        camera_info = data.camera_info
        return uniforms(
            data.ctx,
            JA_CAMERA_SCALED_FACTOR=camera_info.scaled_factor,
            JA_CAMERA_CENTER=camera_info.center,
            JA_CAMERA_LOC=camera_info.camera_location,
            JA_CAMERA_RIGHT=normalize(camera_info.horizontal_vect),
            JA_CAMERA_UP=normalize(camera_info.vertical_vect),
            JA_VIEW_MATRIX=camera_info.view_matrix.T.flatten(),
            JA_FIXED_DIST_FROM_PLANE=camera_info.fixed_distance_from_plane,
            JA_PROJ_MATRIX=camera_info.proj_matrix.T.flatten(),
            JA_FRAME_RADIUS=camera_info.frame_radius,
            JA_ANTI_ALIAS_RADIUS=data.anti_alias_radius,
            JA_LIGHT_SOURCE=data.light_source_location,
        )

    _RenderCollectionCls = RenderCollection

    def _get_render_collection(self, global_t: float) -> RenderCollection:
        # 提取所有当前可见的 apprs
        apprs: list[tuple[ItemAppearance, Item]] = []
        for _, appr in self.visible_item_segments.get(global_t):
            if not appr.is_visible_at(global_t):
                continue
            data = appr.stack.compute(global_t, True)
            apprs.append((appr, data))

        # 提取所有当前可见的额外渲染
        extras: list[tuple[Timeline.ExtraRenderGroup, RenderGroupReturn]] = []
        for rg in self.visible_render_group_segments.get(global_t):
            if not rg.t_range.contains(global_t):
                continue
            extra_items = rg.func()
            extras.append((rg, extra_items))

        # 组装为 RenderCollection 并依次调用将要渲染的物件的 hook，以便例如 FrameEffect 代理与其相关联的物件的渲染
        collection = self._RenderCollectionCls(self.timeline, apprs, extras)
        for item in collection.iter_items():
            item._render_collection_hook(collection)

        return collection

    def capture(
        self, global_t: float, *, transparent: bool = True, ctx: mgl.Context | None = None
    ) -> Image.Image:
        if ctx:
            log.debug(f'Reusing context {ctx} for `capture`')
            apply_blend_flags(ctx)
        else:
            if self.capture_ctx is None:
                log.debug('Initializing OpenGL context for `capture` ..')
                self.capture_ctx = create_context_430_or_330(standalone=True)
                log.debug('Created OpenGL context for `capture`')
            ctx = self.capture_ctx

        # 虽然说当前设计的情况中不会出现
        # 但是出于稳健性的考虑，这里还是判断，如果这次使用的 ctx 与上次的不同，则销毁原有的 framebuffer
        if self.capture_framebuffer is not None and self.capture_framebuffer.ctx is not ctx:
            self.capture_framebuffer.release()
            self.capture_framebuffer = None

        # 在没有创建 framebuffer 的时候创建一份用于渲染
        if self.capture_framebuffer is None:
            pw, ph = self.cfg.pixel_width, self.cfg.pixel_height
            self.capture_framebuffer = FrameBuffer(
                ctx, pw, ph, self.cfg.background_color.rgb, transparent
            )

        fbo = self.capture_framebuffer
        with fbo.context():
            fbo.clear()
            self.render_all(ctx, global_t)
            fbo.unpremultiply()

        return fbo.get_image()

    def to_item(self, **kwargs) -> TimelineItem:
        """
        使用该方法可以在一个 Timeline 中插入另一个 Timeline

        例如：

        .. code-block:: python

            class Sub1(Timeline):
                def construct(self):
                    text = Text('text from Sub1')
                    text.points.shift(UP)
                    self.play(
                        Rotate(text, TAU, about_point=LEFT * 2),
                        duration=4
                    )


            class Sub2(Timeline):
                def construct(self):
                    text = Text('text from Sub2')
                    text.points.shift(DOWN)
                    self.play(
                        Rotate(text, TAU, about_point=RIGHT * 2),
                        duration=4
                    )


            class Test(Timeline):
                def construct(self):
                    tl1 = Sub1().build().to_item().show()
                    tl2 = Sub2().build().to_item().show()
                    self.forward_to(tl2.end)

        这个例子中，在 ``Test`` 中插入了 ``Sub1`` 和 ``Sub2``

        额外参数：

        - ``delay``: 延迟多少秒开始该 Timeline 的播放
        - ``first_frame_duration``: 第一帧持续多少秒
        - ``keep_last_frame``: 是否在 Timeline 结束后仍然保留最后一帧的显示
        """
        self._warning_if_has_gui_command()
        return TimelineItem(self, **kwargs)

    def to_playback_control_item(self, **kwargs) -> TimelinePlaybackControlItem:
        """
        使用该方法可以在一个 Timeline 中插入另一个 Timeline

        并且与 :class:`~.Video` 类似，可以使用 ``start``、``stop`` 以及 ``seek`` 控制播放进度

        例：

        .. code-block:: python

            class Sub(Timeline):
                def construct(self):
                    self.play(
                        ItemUpdater(
                            None,
                            lambda p: Text(f'{p.global_t:.2f}')
                        ),
                        duration=8
                    )


            class Test(Timeline):
                def construct(self):
                    sub = Sub().build().to_playback_control_item().show()
                    sub.start()
                    self.forward(2)
                    sub.start(speed=0.1)
                    self.forward(2)
                    sub.seek(0).start(speed=4)
                    self.forward(2)

        .. warning::

            在默认情况下未开始播放，需要使用 ``start`` 以开始播放

        额外参数：

        - ``keep_last_frame``: 是否在 Timeline 结束后仍然保留最后一帧的显示
        """
        self._warning_if_has_gui_command()
        return TimelinePlaybackControlItem(self, **kwargs)

    def _warning_if_has_gui_command(self) -> None:
        command = self.timeline.gui_command
        if command is not None:
            log.warning(
                _(
                    'GUI command in a sub-Timeline is ignored; defined in "{file}" at line {lineno}'
                ).format(
                    file=os.path.basename(command.filepath),
                    lineno=command.lineno,
                )
            )


class TimelineItem(Item):
    """
    详见 :meth:`BuiltTimeline.to_item`
    """

    class TIRenderer(Renderer):
        def render(self, item: TimelineItem):
            t = Animation.global_t_ctx.get() - item.at

            if 0 <= t <= item.duration:
                if t < item.first_frame_duration:
                    item._built.render_all(self.data_ctx.get().ctx, 0)
                else:
                    item._built.render_all(self.data_ctx.get().ctx, t - item.first_frame_duration)
            elif item.keep_last_frame and t > item.duration:
                item._built.render_all(self.data_ctx.get().ctx, item._built.duration)

    renderer_cls = TIRenderer

    def __init__(
        self,
        built: BuiltTimeline,
        *,
        delay: float = 0,
        first_frame_duration: float = 0,
        keep_last_frame: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._built = built
        self.at = self.timeline.current_time + delay
        self.first_frame_duration = first_frame_duration
        self.duration = first_frame_duration + self._built.duration
        self.keep_last_frame = keep_last_frame

        parent_timeline = Timeline.get_context(raise_exc=False)
        if parent_timeline is not None:
            parent_timeline.subtimeline_items.append(self)

    def start(self) -> Self:
        """
        从当前时刻开始播放子时间轴，在此时刻之前保持显示第一帧
        """
        parent_timeline = Timeline.get_context()
        current_time = parent_timeline.current_time
        if self.at > current_time:
            self.at = current_time
        self.first_frame_duration = current_time - self.at
        self.duration = self.first_frame_duration + self._built.duration
        return self

    @property
    def end(self) -> float:
        return self.at + self.duration


class PlaybackControl:
    def __init__(self, *args, loop: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.loop = loop

        self.timeline = Timeline.get_context()

        self.actions: list[tuple[float, float, float]] = []

    def start(self, *, speed: int = 1) -> Self:
        if not self.actions:
            base = 0
        else:
            x, y, last_speed = self.actions[-1]
            base = y + (self.timeline.current_time - x) * last_speed

        self.actions.append((self.timeline.current_time, base, speed))
        return self

    def stop(self) -> Self:
        self.start(speed=0)
        return self

    def seek(self, t: float) -> Self:
        if not self.actions:
            speed = 0
        else:
            speed = self.actions[-1][2]
        self.actions.append((self.timeline.current_time, t, speed))
        return self

    def compute_time(self, t: float, total: float | None = None) -> float:
        if not self.actions:
            return 0
        idx = bisect(self.actions, t, key=lambda v: v[0]) - 1
        if idx < 0:
            return 0
        x, y, speed = self.actions[idx]
        result = y + (t - x) * speed

        if total is not None and self.loop:
            return result % total
        return result


class TimelinePlaybackControlItem(PlaybackControl, Item):
    """
    详见 :meth:`BuiltTimeline.to_playback_control_item`
    """

    class TPCIRenderer(Renderer):
        def render(self, item: TimelinePlaybackControlItem):
            t = Animation.global_t_ctx.get()
            t = item.compute_time(t, item.duration)
            t = max(0, t)
            if 0 <= t <= item.duration:
                item._built.render_all(self.data_ctx.get().ctx, t)
            elif item.keep_last_frame and t > item.duration:
                item._built.render_all(self.data_ctx.get().ctx, item._built.duration)

    renderer_cls = TPCIRenderer

    def __init__(self, built: BuiltTimeline, *, keep_last_frame: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._built = built
        self.duration = self._built.duration
        self.keep_last_frame = keep_last_frame
