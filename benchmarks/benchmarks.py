from __future__ import annotations

from typing import TYPE_CHECKING

from janim import examples

from .extract_timeline import get_all_timelines_from_module

if TYPE_CHECKING:
    from janim.imports import Timeline

timelines = get_all_timelines_from_module(examples)


def _wrap_timeline(timeline: type[Timeline]):
    from janim.imports import Config, guarantee_existence
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
            'time_write': time_write,
        },
    )


for timeline in timelines:
    suite = _wrap_timeline(timeline)
    globals()[suite.__name__] = suite

timeline = None
