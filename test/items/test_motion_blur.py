import unittest

import numpy as np

from janim.anims.transform import Transform
from janim.constants import RIGHT, UP
from janim.items.geometry.polygon import Square
from janim.items.group import Group
from janim.items.item import Item
from janim.timeline import Timeline
from janim.utils.config import Config


class MovingSquare(Timeline):
    def construct(self):
        square = Square(fill_alpha=1).set_motion_blur().show()
        self.play(square.anim.points.shift(RIGHT * 4))


class StationarySquare(Timeline):
    def construct(self):
        Square(fill_alpha=1).set_motion_blur().show()
        self.forward()


class PlainSquare(Timeline):
    def construct(self):
        Square(fill_alpha=1).show()
        self.forward()


class MixedSquares(Timeline):
    def construct(self):
        blurred = Square(fill_alpha=1).set_motion_blur().show().points.shift(UP * 2).r
        frozen = Square(fill_alpha=1).show().points.shift(-UP * 2).r
        self.play(
            blurred.anim.points.shift(RIGHT * 4),
            frozen.anim.points.shift(RIGHT * 4),
        )


class MixedSquaresNoBlur(Timeline):
    def construct(self):
        blurred = Square(fill_alpha=1).show().points.shift(UP * 2).r
        frozen = Square(fill_alpha=1).show().points.shift(-UP * 2).r
        self.play(
            blurred.anim.points.shift(RIGHT * 4),
            frozen.anim.points.shift(RIGHT * 4),
        )


class TransformSquare(Timeline):
    def construct(self):
        source = Square(fill_alpha=1).set_motion_blur().show()
        target = Square(fill_alpha=1).points.shift(RIGHT * 4).r
        self.play(Transform(source, target))


class NestedBlurredSquare(Timeline):
    """带运动模糊的方块的子时间轴，内部用较长的快门。"""

    CONFIG = Config(motion_blur_shutter=6)

    def construct(self):
        square = Square(fill_alpha=1).set_motion_blur().show()
        self.play(square.anim.points.shift(RIGHT * 4))


class NestedSharpSquare(Timeline):
    """同样的方块，但没有开运动模糊，作为对照。"""

    def construct(self):
        square = Square(fill_alpha=1).show()
        self.play(square.anim.points.shift(RIGHT * 4))


class NestedTimeline(Timeline):
    """把上面两个子时间轴依次放进父时间轴。"""

    def construct(self):
        blurred = NestedBlurredSquare().build(quiet=True).to_item().show()
        self.forward(blurred.duration)
        sharp = NestedSharpSquare().build(quiet=True).to_item().show()
        self.forward(sharp.duration)


class NestedSharpTimeline(Timeline):
    """与 NestedTimeline 结构相同，但子时间轴都没有模糊。"""

    def construct(self):
        first = NestedSharpSquare().build(quiet=True).to_item().show()
        self.forward(first.duration)
        sharp = NestedSharpSquare().build(quiet=True).to_item().show()
        self.forward(sharp.duration)


class CameraSceneMixin:
    """相机从 ―2 匀速移到 +2，同时场景里有一个开了模糊、但自己不动的方块。

    该方块在曝光窗口内是静止的，所以它本身不会糊；
    而相机若不冻结在 center_t，整幅画面都会被相机的运动拉丝。
    """

    camera_moves = True

    def construct(self):
        Square(fill_alpha=1).set_motion_blur().show()
        self.play(self.camera.anim.points.shift(RIGHT * 4), duration=1)


class MovingCameraWithBlurredItem(CameraSceneMixin, Timeline):
    camera_moves = True


class StillCameraWithBlurredItem(CameraSceneMixin, Timeline):
    """相机不动的对照。"""

    camera_moves = False

    def construct(self):
        Square(fill_alpha=1).set_motion_blur().show()
        # 用同样时长的 forward，并让相机初始位置就在中点，
        # 这样它在 t=0.5 的位置与 MovingCamera 版本一致
        self.camera.points.shift(RIGHT * 2)
        self.forward(1)


class MarkedCameraWithBlurredItem(CameraSceneMixin, Timeline):
    """相机自己开了模糊 —— 此时相机的运动才应当被计入曝光。"""

    camera_moves = True

    def construct(self):
        Square(fill_alpha=1).set_motion_blur().show()
        self.camera.set_motion_blur()
        self.play(self.camera.anim.points.shift(RIGHT * 4), duration=1)


class MotionBlurTest(unittest.TestCase):
    def test_item_state(self):
        child = Item()
        group = Group(child)
        self.assertFalse(group.is_motion_blur_enabled())
        group.set_motion_blur(root_only=True)
        self.assertTrue(group.is_motion_blur_enabled())
        self.assertFalse(child.is_motion_blur_enabled())
        group.set_motion_blur()
        self.assertTrue(child.is_motion_blur_enabled())
        copy = group.copy()
        self.assertTrue(copy[0].is_motion_blur_enabled())
        copy.set_motion_blur(False)
        self.assertFalse(copy.not_changed(group))
        copy.become(group)
        self.assertTrue(copy.is_motion_blur_enabled())

    def test_exposure(self):
        with Config(pixel_width=96, pixel_height=54, fps=12, motion_blur_samples=4):
            moving = MovingSquare().build(quiet=True)
            stationary = StationarySquare().build(quiet=True)
            plain = PlainSquare().build(quiet=True)
            blurred = np.asarray(moving.capture(0.5))
            regular = np.asarray(stationary.capture(0.5))
            original = np.asarray(plain.capture(0.5))
            self.assertEqual(blurred.shape, (54, 96, 4))
            self.assertGreater(blurred.sum(), 0)
            np.testing.assert_array_equal(regular, original)
            self.assertTrue(np.any((blurred[:, :, 3] > 0) & (blurred[:, :, 3] < 255)))

    def test_mixed_and_transform(self):
        with Config(pixel_width=96, pixel_height=54, fps=12, motion_blur_samples=4):
            mixed = MixedSquares().build(quiet=True)
            regular = MixedSquaresNoBlur().build(quiet=True)
            transformed = TransformSquare().build(quiet=True)
            image = np.asarray(mixed.capture(0.5))
            normal_image = np.asarray(regular.capture(0.5))
            transformed_image = np.asarray(transformed.capture(0.5))
            np.testing.assert_array_equal(image[30:], normal_image[30:])
            self.assertFalse(np.array_equal(image[:24], normal_image[:24]))
            self.assertGreater(transformed_image[:, :, 3].sum(), 0)
            self.assertTrue(
                np.any((transformed_image[:, :, 3] > 0) & (transformed_image[:, :, 3] < 255))
            )

    def test_nested_timeline(self):
        """子 Timeline 放进父 Timeline 后，仍然使用它自己的曝光设定。

        曾经的问题：``TimelineItem`` 的渲染器调用 ``render_all`` 而非 ``render_frame``，
        于是子 Timeline 的 ``motion_blur_shutter`` 完全不起作用 —— 单独渲染有模糊，
        套进父 Timeline 就变成清晰的一帧。
        """
        with Config(pixel_width=96, pixel_height=54, fps=12, motion_blur_samples=4):
            blurred = NestedBlurredSquare().build(quiet=True)
            sharp = NestedSharpSquare().build(quiet=True)
            nested = NestedTimeline().build(quiet=True)
            nested_sharp = NestedSharpTimeline().build(quiet=True)

            standalone = np.asarray(blurred.capture(0.5))
            sharp_standalone = np.asarray(sharp.capture(0.5))

            # 1) 带模糊的子时间轴，在父时间轴里的渲染应当与它单独渲染完全一致
            np.testing.assert_array_equal(np.asarray(nested.capture(0.5)), standalone)
            # 2) 全清晰的父时间轴里的子时间轴，也应当与它单独渲染一致
            np.testing.assert_array_equal(np.asarray(nested_sharp.capture(0.5)), sharp_standalone)
            # 3) 两条对照确实不同 —— 说明第 1 条的一致不是因为模糊整体失效
            self.assertFalse(np.array_equal(standalone, sharp_standalone))
            # 4) 模糊确实在半透明区域留下了痕迹
            self.assertTrue(np.any((standalone[:, :, 3] > 0) & (standalone[:, :, 3] < 255)))

    def test_camera_motion(self):
        """相机没开模糊时，相机的运动不该被计入曝光。

        曾经的问题：``render_all`` 总是按采样时刻 ``global_t`` 求值相机，
        而普通物件会被冻结在 ``center_t``。于是只要场景里**任意一个**物件开了
        运动模糊，相机自身的运动就会把整个画面糊掉 —— 哪怕没有任何人要求。
        """
        with Config(pixel_width=96, pixel_height=54, fps=12, motion_blur_samples=4):
            moving = MovingCameraWithBlurredItem().build(quiet=True)
            still = StillCameraWithBlurredItem().build(quiet=True)
            marked = MarkedCameraWithBlurredItem().build(quiet=True)

            # t=0.5 时两台相机位置相同，场景内容也相同 ⇒ 应当逐像素一致
            moving_image = np.asarray(moving.capture(0.5))
            still_image = np.asarray(still.capture(0.5))
            np.testing.assert_array_equal(moving_image, still_image)

            # 相机自己开了模糊，运动才应当被计入 —— 此时结果必须与上面不同
            marked_image = np.asarray(marked.capture(0.5))
            self.assertFalse(np.array_equal(marked_image, moving_image))
