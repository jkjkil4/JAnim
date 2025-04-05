import os
import cv2
import sys
import unittest

import numpy as np

import janim.examples as examples
from janim.anims.timeline import Timeline
from janim.cli import get_all_timelines_from_module
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
        def __init__(self, timeline_cls: type[Timeline]):
            super().__init__('test')
            self.timeline_cls = timeline_cls

        def __str__(self) -> str:
            return f"{self.timeline_cls.__name__} ({self.__class__.__name__})"

        def test(self) -> None:
            with Config(pixel_width=WIDTH,
                        pixel_height=HEIGHT,
                        fps=5,
                        temp_dir='test/__test_tempdir__'):
                built = self.timeline_cls().build(quiet=True)

            fps = built.cfg.fps

            worst = 1
            frame_number = -1

            for frame, ref_image in zip(range(round(built.duration * fps) + 1),
                                        self.get_ref(self.timeline_cls.__name__)):
                render_image = cv2.cvtColor(np.array(built.capture(frame / fps)), cv2.COLOR_RGBA2BGRA)
                res = cv2.matchTemplate(render_image, ref_image, cv2.TM_CCOEFF_NORMED)
                res = res[0][0]
                if res < 0.98 and res < worst:
                    worst = res
                    frame_number = frame

            if worst != 1:
                guarantee_existence('test/__test_errors__')
                built.capture(frame_number / fps).save(f'test/__test_errors__/{self.timeline_cls.__name__}_{frame_number}_err.png')
            self.assertEqual(worst, 1, f'worst: {worst}, t: {frame_number / fps}')

        @staticmethod
        def get_ref(timeline_name: str):
            frame = 0
            ref = None
            while True:
                ref_path = os.path.join(ref_dir, f'{timeline_name}_{frame}.png')
                if os.path.exists(ref_path):
                    ref = cv2.imread(ref_path, cv2.IMREAD_UNCHANGED)
                assert ref is not None
                frame += 1
                yield ref


    ref_dir = get_ref_dir()
    timelines = get_timelines_for_test()
    suite = unittest.TestSuite()
    suite.addTests([
        ExampleTester(timeline)
        for timeline in timelines
    ])
    return suite


def generate_ref() -> None:
    includes = sys.argv[1:]
    output_dir = guarantee_existence(get_ref_dir())

    with Config(pixel_width=WIDTH,
                pixel_height=HEIGHT,
                fps=5):
        for timeline in get_timelines_for_test():
            if includes and timeline.__name__ not in includes:
                continue
            built = timeline().build()
            fps = built.cfg.fps
            prev_bytes = None
            for frame in range(round(built.duration * fps) + 1):
                current = built.capture(frame / fps)
                current_bytes = current.tobytes()
                if prev_bytes is not None and prev_bytes == current_bytes:
                    continue
                current.save(os.path.join(output_dir, f'{timeline.__name__}_{frame}.png'))
                prev_bytes = current_bytes


if __name__ == '__main__':
    print('Warning: 直接执行该文件会进行样例视频输出，作为单元测试样例，确认继续执行吗？')
    print('Warning: Running this file will generate sample video output for unit testing purposes. '
          'Are you sure you want to proceed?')
    ret = input('(y/N): ')
    if ret.lower() == 'y':
        generate_ref()
