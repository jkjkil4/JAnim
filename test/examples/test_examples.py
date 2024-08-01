import os
import subprocess as sp
import sys
import unittest
from typing import Generator

import numpy as np

import janim.examples as examples
from janim.anims.timeline import Timeline
from janim.cli import get_all_timelines_from_module
from janim.render.writer import VideoWriter
from janim.utils.config import Config
from janim.utils.file_ops import guarantee_existence

sys.path.append(os.path.dirname(__file__))

import examples_of_animations as anim_examples
import examples_of_bugs as bug_examples

WIDTH = 192 * 2
HEIGHT = 108 * 2


def get_ref_dir() -> str:
    return os.path.join(os.path.dirname(__file__), 'ref')


def get_timelines_for_test() -> list[type[Timeline]]:
    timelines: list[type[Timeline]] = []
    timelines += get_all_timelines_from_module(examples)
    timelines += get_all_timelines_from_module(anim_examples)
    timelines += get_all_timelines_from_module(bug_examples)
    return timelines


def load_tests(loader, standard_tests, pattern) -> unittest.TestSuite:
    class ExampleTester(unittest.TestCase):
        def __init__(self, timeline_cls: type[Timeline], ref_path: str):
            super().__init__('test')
            self.timeline_cls = timeline_cls
            self.ref_path = ref_path

        def __str__(self) -> str:
            return f"{self.timeline_cls.__name__} ({self.__class__.__name__})"

        def test(self) -> None:
            temp_file = os.path.join(Config.get.temp_dir, 'test_example.mov')

            with Config(pixel_width=WIDTH,
                        pixel_height=HEIGHT,
                        fps=5):
                anim = self.timeline_cls().build(quiet=True)
                VideoWriter.writes(anim, temp_file, quiet=True)

            render_frames = self.get_frames(temp_file)
            ref_frames = self.get_frames(self.ref_path)

            for buf1, buf2 in zip(render_frames, ref_frames, strict=True):
                render_data = np.frombuffer(buf1, dtype=np.uint8).astype(np.int16)
                ref_data = np.frombuffer(buf2, dtype=np.uint8).astype(np.int16)
                delta = np.abs(render_data - ref_data)
                error = delta.sum()
                assert error == 0

        @staticmethod
        def get_frames(video_path: str) -> Generator[bytes, None, None]:
            ffmpeg_command = [
                'ffmpeg',
                '-i', video_path,
                '-f', 'rawvideo',
                '-pix_fmt', 'rgba',
                '-'
            ]
            process = sp.Popen(ffmpeg_command, stdout=sp.PIPE, stderr=sp.PIPE)

            while raw_frame := process.stdout.read(HEIGHT * WIDTH * 4):
                yield raw_frame

    path = get_ref_dir()
    timelines = get_timelines_for_test()
    suite = unittest.TestSuite()
    suite.addTests([
        ExampleTester(timeline, os.path.join(path, f'{timeline.__name__}.mov'))
        for timeline in timelines
    ])
    return suite


def generate_ref() -> None:
    includes = sys.argv[1:]
    output_dir = guarantee_existence(get_ref_dir())

    with Config(pixel_width=WIDTH,
                pixel_height=HEIGHT,
                fps=5,
                output_dir=output_dir):
        for timeline in get_timelines_for_test():
            if includes and timeline.__name__ not in includes:
                continue
            VideoWriter.writes(timeline().build(),
                               os.path.join(output_dir, f'{timeline.__name__}.mov'))


if __name__ == '__main__':
    print('Warning: 直接执行该文件会进行样例视频输出，作为单元测试样例，确认继续执行吗？')
    print('Warning: Running this file will generate sample video output for unit testing purposes. '
          'Are you sure you want to proceed?')
    ret = input('(y/N): ')
    if ret.lower() == 'y':
        generate_ref()
