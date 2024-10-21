import inspect

import janim.examples as examples
from janim.imports import Config, Timeline


def get_all_timelines_from_module(module) -> list[type[Timeline]]:
    '''
    从指定的 ``module`` 中得到所有可用的 :class:`~.Timeline`
    '''
    classes = [
        value
        for value in module.__dict__.values()
        if (isinstance(value, type)
            and issubclass(value, Timeline)
            and value.__module__ == module.__name__                             # 定义于当前模块，排除了 import 导入的
            and not getattr(value.construct, '__isabstractmethod__', False))    # construct 方法已被实现
    ]
    if len(classes) <= 1:
        return classes

    classes.sort(key=lambda cls: inspect.getsourcelines(cls)[1])

    return classes


timelines = get_all_timelines_from_module(examples)


def _wrap_timeline(timeline: type[Timeline]):
    from janim.imports import guarantee_existence
    from janim.render.writer import VideoWriter

    def setup(self):
        guarantee_existence('_asv_videos')
        with Config(fps=10):
            self.built_anim = timeline().build()
        self.file_path = f'_asv_videos/{timeline.__name__}.mp4'

    def time_build(self):
        timeline().build()

    def time_write(self):
        VideoWriter.writes(self.built_anim, self.file_path)

    return type(
        f'Time_{timeline.__name__}',
        tuple(),
        {
            'setup': setup,
            'time_build': time_build,
            'time_write': time_write
        }
    )


for timeline in timelines:
    suite = _wrap_timeline(timeline)
    globals()[suite.__name__] = suite

timeline = None
