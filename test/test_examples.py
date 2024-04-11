import inspect
import unittest

import numpy as np

import janim.examples as examples
from janim.anims.timeline import Timeline


class TestExamples(unittest.TestCase):
    def test_examples(self) -> None:
        classes = [
            value
            for value in examples.__dict__.values()
            if isinstance(value, type) and issubclass(value, Timeline) and value.__module__ == examples.__name__
        ]
        classes.sort(key=lambda x: inspect.getsourcelines(x)[1])

        for timeline_cls in classes:
            anim = timeline_cls().build(quiet=True)
            for t in np.arange(0, anim.global_range.duration, 0.5):
                anim.anim_on(t)
            anim.anim_on(anim.global_range.duration)
