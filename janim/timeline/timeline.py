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
from dataclasses import dataclass
from contextvars import ContextVar
from typing import Literal, NoReturn, Self, overload

import moderngl as mgl
import numpy as np
from janim_backend import gl
from janim_backend.relation import CutType
from PIL import Image

from janim.anims_core.anim_stack import simplify_anim_stacks
from janim.anims_core.animation import Animation
from janim.anims_core.time import FOREVER, TimeChunks, TimeRange
from janim.camera.camera import Camera
from janim.camera.camera_info import CameraInfo
from janim.constants import DEFAULT_DURATION
from janim.exception import TimelineLookupError
from janim.items.item import Item
from janim.items.points import Point
from janim.items.relation import _items_relation_registry
from janim.locale import get_translator
from janim.logger import log
from janim.render.base import RenderData, Renderer, apply_blend_flags, create_context_430_or_330
from janim.render.collection import RenderCollection
from janim.render.framebuffer import FrameBuffer
from janim.render.motion_blur import MotionBlurBuffer
from janim.render.uniform import uniforms
from janim.timeline.core import ExtraRenderGroup, ItemAppearance, RenderGroupReturn, TimelineCore
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

    def build(self, *, quiet=False, hide_subtitles=False, show_debug_notice=False) -> BuiltTimeline:
        """
        构建动画并返回
        """
        with self._build_context(inspect.currentframe(), quiet) as build_ctx:
            indent_str = build_ctx.indent_str
            quiet = build_ctx.quiet

            self.hide_subtitles = hide_subtitles
            self.show_debug_notice = show_debug_notice

            if not quiet:  # pragma: no cover
                log.info(indent_str + _('Building "{name}"').format(name=self.__class__.__name__))
                start_time = time.time()

            self.camera = Camera()
            self.track(self.camera)

            self.light_source = Point([-9, -7, 10])
            self.track(self.light_source)

            try:
                self.construct()
            except Timeline.GuiCommandInterrupt as e:
                self.gui_command = e.command

                # 使用 GUI 命令的时候，额外产生一点时间，避免最后一帧的效果不可预览的问题
                self.forward(DEFAULT_DURATION, _record_lineno=False)

                if not quiet:  # pragma: no cover
                    msg = _(
                        'Due to the use of a GUI command, '
                        '"{name}" automatically generated an additional duration of {duration}s'
                    ).format(
                        name=self.__class__.__name__,
                        duration=DEFAULT_DURATION,
                    )
                    log.info(indent_str + msg)

            if self.current_time == 0:
                # 使得没有任何前进时，产生一点时间，避免除零以及其它问题
                self.forward(DEFAULT_DURATION, _record_lineno=False)

                if not quiet:  # pragma: no cover
                    msg = _(
                        '"{name}" did not produce a duration after construction, '
                        'automatically generated a duration of {duration}s'
                    ).format(
                        name=self.__class__.__name__,
                        duration=DEFAULT_DURATION,
                    )
                    log.info(indent_str + msg)

            for appr in self.item_appearances.values():
                appr.stack.clear_cache()  # TODO: 检查这句是否有必要，并说明原因

            built = BuiltTimeline(self)

            if not quiet:  # pragma: no cover
                elapsed = time.time() - start_time  # type: ignore
                msg = _('Finished building "{name}" in {elapsed:.2f} s').format(
                    name=self.__class__.__name__,
                    elapsed=elapsed,
                )
                log.info(build_ctx.indent_str + msg)

        return built

    @dataclass(frozen=True, slots=True)
    class _BuildContext:
        indent: int
        indent_str: str
        quiet: bool

    _build_ctx: ContextVar[_BuildContext] = ContextVar('Timeline.build_ctx')

    @contextmanager
    def _build_context(self, build_frame: types.FrameType | None, quiet: bool):
        """
        进入 ``build`` 有关的上下文环境，并进行一些相关的配置

        会 ``yield _BuildContext``，作为 ``as build_ctx`` 使用
        """
        parent_ctx = self._build_ctx.get(None)

        indent = 0 if parent_ctx is None else parent_ctx.indent + 2
        quiet = quiet if parent_ctx is None else quiet or parent_ctx.quiet

        build_ctx = self._BuildContext(indent=indent, indent_str='  ' * indent, quiet=quiet)
        with (
            self.config_context(),
            ContextSetter(self.ctx_var, self),
            ContextSetter(self._build_ctx, build_ctx),
        ):
            # 记录 frame 对象，用于 TimelineCore._extract_lineno_in_construct
            self._build_frame = build_frame

            # 在 build 期间关闭 gc，这样只有重新 enable 之后的一次大 gc，这样可以提升效率
            gc_enabled = gc.isenabled()
            gc.disable()

            # 构建期间使用 Continous，构建之后切换到 Discrete，因为
            # - 构建期间产生的大多为长生命周期的 registry nodes，使用 Continous
            # - 构建之后会由于 ItemUpdater / StepUpdater 等因素导致大量的临时 registry nodes，使用 Discrete 便于回收 dead nodes
            if parent_ctx is None:  # 如果是 sub-timeline 则跳过该操作
                _items_relation_registry.cut_nodes_chunk(CutType.Continous)

            try:
                yield build_ctx
            finally:
                self._build_frame = None  # 设置为 None 避免长期持有 frame 对象
                if gc_enabled:
                    gc.enable()

                if parent_ctx is None:
                    _items_relation_registry.cut_nodes_chunk(CutType.Discrete)

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

            # 也用于 `BuiltTimeline.cfg`，可参考其文档
            self.cfg: Config | ConfigGetter = ConfigGetter(self._config_context)

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

    def __call__(self, command_text: str) -> NoReturn:
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
        simplify_anim_stacks([appr.stack for appr in timeline.item_appearances.values()])

        self.visible_item_chunks = TimeChunks(
            ((item, appr) for item, appr in timeline.item_appearances.items()),
            lambda x: (
                TimeRange(*range) if len(range) == 2 else TimeRange(*range, self.duration + 1)  # type: ignore
                for range in it.batched(x[1].visibility, 2)
            ),
        )
        self.visible_render_group_chunks = TimeChunks(
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
        self._motion_blur_buffer: MotionBlurBuffer | None = None

    @property
    def cfg(self) -> Config | ConfigGetter:
        """
        可以使用该属性获取 Timeline 构建时的上下文中的配置

        可用于在简单场景中避免使用 :meth:`config_context` ，例如：

        .. code-block:: python

            built.cfg.preview_fps
        """
        return self.timeline.cfg

    @property
    def frame_count(self) -> int:
        return round(self.duration * self.cfg.fps) + 1

    def get_audio_samples_of_frame(
        self, fps: int, framerate: int, frame: int, *, count: int = 1
    ) -> np.ndarray:
        """
        提取特定帧的音频流
        """
        begin = frame / fps
        end = (frame + count) / fps
        return self.get_audio_samples_between(framerate, begin, end)

    def get_audio_samples_between(
        self,
        framerate: int,
        begin: float,
        end: float,
    ) -> np.ndarray:
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
            data = built.get_audio_samples_between(framerate, begin - item.at, end - item.at)
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
        center_t: float | None = None,
    ) -> bool:
        """
        渲染所有可见物件
        """
        timeline = self.timeline
        global_t = timeline.time_aligner.align(global_t)
        if center_t is not None:
            center_t = timeline.time_aligner.align(center_t)
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
                # 与普通物件用同一条曝光规则：只有它们自己开了运动模糊才按采样时刻求值，
                # 否则冻结在 center_t
                if camera is None:
                    camera = timeline.compute_item(
                        timeline.camera,
                        self._exposure_time(timeline.camera, global_t, center_t),
                        True,
                    )
                camera_info = camera.points.info
                light_source = timeline.compute_item(
                    timeline.light_source,
                    self._exposure_time(timeline.light_source, global_t, center_t),
                    True,
                )
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
                    collection = self._get_render_collection(global_t, center_t)

                    # 进行渲染
                    collection.render()

        except Exception:
            traceback.print_exc()
            return False

        return True

    def _exposure_time(self, item: Item, global_t: float, center_t: float | None) -> float:
        """
        决定 ``item`` 该按哪个时刻求值。

        与 :meth:`_get_render_collection` 中对普通物件使用的规则一致：
        只有自己开了运动模糊的物件才按曝光窗口内的采样时刻 ``global_t`` 求值，
        其余一律冻结在 ``center_t``。
        """
        if center_t is None:
            return global_t
        appr = self.timeline.item_appearances.get(item)
        if appr is not None and appr.stack.compute(center_t, True)._motion_blur:
            return global_t
        return center_t

    def _uniforms_context(self, data: RenderData):
        camera_info = data.camera_info
        U = gl.FastUniform
        return uniforms(
            data.ctx,
            JA_CAMERA_SCALED_FACTOR=(U.write_float, camera_info.scaled_factor),
            JA_CAMERA_CENTER=(U.write_bytes, camera_info.center.tobytes()),
            JA_CAMERA_LOC=(U.write_bytes, camera_info.camera_location.tobytes()),
            JA_CAMERA_RIGHT=(U.write_bytes, normalize(camera_info.horizontal_vect).tobytes()),
            JA_CAMERA_UP=(U.write_bytes, normalize(camera_info.vertical_vect).tobytes()),
            JA_VIEW_MATRIX=(U.write_bytes, camera_info.view_matrix.T.tobytes()),
            JA_FIXED_DIST_FROM_PLANE=(U.write_float, camera_info.fixed_distance_from_plane),
            JA_PROJ_MATRIX=(U.write_bytes, camera_info.proj_matrix.T.tobytes()),
            JA_FRAME_RADIUS=(U.write_bytes, camera_info.frame_radius.tobytes()),
            JA_ANTI_ALIAS_RADIUS=(U.write_float, data.anti_alias_radius),
            JA_LIGHT_SOURCE=(U.write_bytes, data.light_source_location.tobytes()),
        )

    def release_motion_blur_buffer(self, ctx: mgl.Context | None = None) -> None:
        buffer = self._motion_blur_buffer
        if buffer is not None and (ctx is None or buffer.ctx is ctx):
            buffer.release()
            self._motion_blur_buffer = None

    def render_frame(
        self, ctx: mgl.Context, global_t: float, *, camera: Camera | None = None
    ) -> bool:
        """Render one exposed frame into the currently bound framebuffer."""
        cfg = self.cfg
        if not cfg.motion_blur:
            return self.render_all(ctx, global_t, camera=camera)

        center_t = self.timeline.time_aligner.align(global_t)
        with (
            ContextSetter(Animation.global_t_ctx, center_t),
            ContextSetter(Timeline.ctx_var, self.timeline),
            self.timeline.config_context(),
        ):
            has_blur = any(
                appr.stack.compute(center_t, True)._motion_blur
                for appr in self.timeline.item_appearances.values()
            )
        if not has_blur:
            return self.render_all(ctx, global_t, camera=camera)

        count = cfg.motion_blur_samples
        shutter = cfg.motion_blur_shutter
        if count < 1 or shutter < 0 or not math.isfinite(shutter):
            raise ValueError(
                'motion_blur_samples must be positive and shutter must be finite and nonnegative'
            )
        if count == 1 or shutter == 0:
            return self.render_all(ctx, global_t, camera=camera)

        size = ctx.fbo.size
        buffer = self._motion_blur_buffer
        if buffer is None or buffer.ctx is not ctx or buffer.size != size:
            self.release_motion_blur_buffer()
            buffer = self._motion_blur_buffer = MotionBlurBuffer(ctx, size)

        buffer.clear()
        exposure = shutter / cfg.fps
        try:
            for idx in range(count):
                sample_t = max(
                    0, min(self.duration, center_t + (idx + 0.5 - count / 2) * exposure / count)
                )
                with buffer.sample.context():
                    buffer.sample.clear()
                    if not self.render_all(ctx, sample_t, camera=camera, center_t=center_t):
                        return False
                buffer.add_sample()
            # Draw onto the framebuffer that is currently bound by the caller,
            # so the Qt widget's own FBO is preserved.
            buffer.resolve(count)
        finally:
            self._time = center_t
        return True

    _RenderCollectionCls = RenderCollection

    def _get_render_collection(
        self, global_t: float, center_t: float | None = None
    ) -> RenderCollection:
        # The center-time state determines whether each tracked item participates in exposure.
        apprs: list[tuple[ItemAppearance, Item]] = []
        frozen_renderers: dict[ItemAppearance, float] = {}
        candidates = (
            self.visible_item_chunks.get(global_t)
            if center_t is None
            else self.timeline.item_appearances.items()
        )
        for item, appr in candidates:
            at = global_t
            if center_t is not None and not appr.stack.compute(center_t, True)._motion_blur:
                at = center_t
            if not appr.is_visible_at(at):
                continue
            apprs.append((appr, appr.stack.compute(at, True)))
            if at != global_t:
                # A frozen Video or nested Timeline must also read center-time in its renderer.
                frozen_renderers[appr] = at

        # Extra render groups (e.g. Transform) are sampled as a whole.
        extras: list[tuple[ExtraRenderGroup, RenderGroupReturn]] = []
        groups = (
            self.visible_render_group_chunks.get(global_t)
            if center_t is None
            else self.timeline.extra_render_groups
        )
        for rg in groups:
            at = global_t
            if (
                center_t is not None
                and rg.related_items
                and not any(
                    self.timeline.compute_item(item, center_t, True)._motion_blur
                    for item in rg.related_items
                )
            ):
                at = center_t
            if not rg.t_range.contains(at):
                continue
            with ContextSetter(Animation.global_t_ctx, at):
                extra_items = rg.func()
            if at != global_t:
                extra_items = [
                    (item, self._render_at_time(render, at)) for item, render in extra_items
                ]
            extras.append((rg, extra_items))

        # 组装为 RenderCollection 并依次调用将要渲染的物件的 hook，以便例如 FrameEffect 代理与其相关联的物件的渲染
        collection = self._RenderCollectionCls(self.timeline, apprs, extras)
        collection.frozen_renderers = frozen_renderers
        for _, item in apprs:
            item._render_collection_hook(collection)
        for rg, renders in extras:
            at = global_t
            if (
                center_t is not None
                and rg.related_items
                and not any(
                    self.timeline.compute_item(item, center_t, True)._motion_blur
                    for item in rg.related_items
                )
            ):
                at = center_t
            with ContextSetter(Animation.global_t_ctx, at):
                for item, _ in renders:
                    item._render_collection_hook(collection)

        return collection

    @staticmethod
    def _render_at_time(render, at: float):
        def wrapped(item):
            with ContextSetter(Animation.global_t_ctx, at):
                render(item)

        return wrapped

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
                ctx,
                pw,
                ph,
                self.cfg.background_color.rgb,  # type: ignore
                transparent,
            )

        fbo = self.capture_framebuffer
        with fbo.context():
            fbo.clear()
            self.render_frame(ctx, global_t)
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

            # 这里必须调用 render_frame 而不是 render_all：
            # 子 Timeline 有它自己的曝光设定（尤其是它自己的 motion_blur_shutter），
            # 只有 render_frame 才会创建 MotionBlurBuffer 并把这份设定用上。
            # 用 render_all 的话，子 Timeline 内部的 _motion_blur 不会产生任何效果，
            # 于是「单独渲染有模糊、放进父 Timeline 就没模糊」。
            ctx = self.data_ctx.get().ctx

            if 0 <= t <= item.duration:
                if t < item.first_frame_duration:
                    item._built.render_frame(ctx, 0)
                else:
                    item._built.render_frame(ctx, t - item.first_frame_duration)
            elif item.keep_last_frame and t > item.duration:
                item._built.render_frame(ctx, item._built.duration)

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

        assert self.timeline is not None

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

    def start(self, *, speed: float = 1) -> Self:
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
            # 与 TimelineItem.TIRenderer 同理：走 render_frame 子 Timeline 才能用自己的曝光设定
            ctx = self.data_ctx.get().ctx
            if 0 <= t <= item.duration:
                item._built.render_frame(ctx, t)
            elif item.keep_last_frame and t > item.duration:
                item._built.render_frame(ctx, item._built.duration)

    renderer_cls = TPCIRenderer

    def __init__(self, built: BuiltTimeline, *, keep_last_frame: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._built = built
        self.duration = self._built.duration
        self.keep_last_frame = keep_last_frame
