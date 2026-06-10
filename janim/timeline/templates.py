import sys
from janim.timeline import BuiltTimeline, Timeline
from janim.utils.data import ContextSetter


class SourceTimeline(Timeline):
    """
    与 :class:`Timeline` 相比，会在背景显示源代码
    """

    def source_object(self) -> object:
        return self.__class__

    def build(self, *, quiet=False, hide_subtitles=False, show_debug_notice=False) -> BuiltTimeline:
        from janim.items.text import SourceDisplayer

        with ContextSetter(self.ctx_var, self), self.config_context():
            self.source_displayer = SourceDisplayer(self.source_object(), depth=10000)
            self.source_displayer.fix_in_frame().show()
        return super().build(
            quiet=quiet,
            hide_subtitles=hide_subtitles,
            show_debug_notice=show_debug_notice,
        )


class ListedTimelines(Timeline):
    """
    指定一组 :class:`Timeline` 实现，将他们依次播放

    示例：

    .. code-block:: python

        class Section0(Timeline):
            def construct(self):
                ...

        class Section1(Timeline):
            def construct(self):
                ...

        class Section2(Timeline):
            def construct(self):
                ...

        class Sections(ListedTimelines):
            includes = [Section1, Section2]
    """

    includes: list[type[Timeline]] = []

    def construct(self):
        """"""
        for cls in self.includes:
            tl = cls().build().to_item().show()
            self.forward(tl.duration)


class AboveTimelines(ListedTimelines):
    """
    依次播放在同文件中先前定义过的所有 :class:`Timeline` 实现

    示例：

    .. code-block:: python

        class Section0(Timeline):
            def construct(self):
                ...

        class Section1(Timeline):
            def construct(self):
                ...

        class Section2(Timeline):
            def construct(self):
                ...

        class Sections(AboveTimelines):
            pass

    可另外使用 ``excludes`` 指定排除项

    示例：

    .. code-block:: python

        ...

        class Sections(AboveTimelines):
            excludes = [Section0]
    """

    excludes: list[type[Timeline]] = []

    def construct(self):
        """"""
        from janim.cli.utils.extract_timeline import get_all_timelines_from_module

        module = sys.modules[self.__class__.__module__]
        timelines = get_all_timelines_from_module(module)

        includes = []

        for cls in timelines:
            if cls is self.__class__:
                break
            if cls in self.excludes:
                continue
            includes.append(cls)

        self.includes = includes
        super().construct()
