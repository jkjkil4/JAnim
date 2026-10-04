.. _motion_blur:

运动模糊
==============

JAnim 支持对物件开启时域运动模糊（temporal motion blur）：渲染一帧时，
在快门时间区间内渲染多个时刻的完整场景并取平均。
高速运动的物件会因此拉出与真实相机快门一致的拖影。

.. note::

    运动模糊默认不对任何物件生效，需要显式调用 :meth:`~.Item.set_motion_blur` 开启。

快速上手
----------------

.. janim-example:: MotionBlurBasic
    :extract-from-test:
    :no-construct:
    :media: _static/tutorial/MotionBlurBasic.mp4
    :ref: :meth:`~.Item.set_motion_blur` :meth:`~.Item.is_motion_blur_enabled`

其中两个方块的运动完全相同，唯一的区别是上方方块调用了 ``set_motion_blur()``：

- 开模糊的方块在每个时间样本中的位置都不同，采样再平均后就成了一条拖影；
- 未开启的方块则被固定在帧中心时刻，因此始终清晰锐利。

``set_motion_blur(False)`` 可以关闭；默认同时作用于后代，传入 ``root_only=True`` 则只修改物件自身。

快门采样机制
----------------

每帧的曝光区间以该帧时间 ``t`` 为中心对称分布，区间的宽度由 ``motion_blur_shutter`` 决定：

.. code-block:: text

    曝光区间 = [t - motion_blur_shutter / fps / 2, t + motion_blur_shutter / fps / 2]

``motion_blur_shutter`` 的单位是 1 / fps（一帧时长），而不是秒。
例如 ``fps=30``、``motion_blur_shutter=6`` 表示每帧曝光 0.2 秒。

.. janim-example:: MotionBlurDiagram
    :extract-from-test:
    :no-construct:
    :media: _static/tutorial/MotionBlurDiagram.png

区间内均匀取 ``motion_blur_samples`` 个时间样本，每个样本都重新渲染整个场景，
然后在浮点纹理中累加、取平均，最后一次性输出。因此：

- 只有开启了模糊的物件会按样本时间求值。未开启的物件被钉在帧中心时刻 ``t``，
  但仍然参与每个样本的遮挡与排序。
- 摄像机也按样本时间求值。如果只移动摄像机而不移动物件，
  那么未开启模糊的世界物件会因为摄像机运动而模糊（它们在每一帧的像平面位置变了）。

采样时刻按下式计算，并会被裁剪到 ``[0, duration]`` 内，避免动画首尾取到画面之外的时间：

.. code-block:: text

    sample_t = t + (i + 0.5 - samples / 2) * (exposure / samples)，i = 0, 1, ..., samples - 1

快门长度的影响
----------------

.. janim-example:: MotionBlurShutterDemo
    :extract-from-test:
    :no-construct:
    :media: _static/tutorial/MotionBlurShutterDemo.mp4

三条跑道的运动完全一致，只是曝光时长不同：

- ``shutter = 0``：等价于不做曝光采样，和没开模糊一样清晰；
- ``shutter = 3``：拖影长度约为物件自身宽度的一半，速度感开始出现；
- ``shutter = 6``：拖影明显超过物件宽度，开始接近"光带"的观感。

拖影长度取决于曝光期间物件走了多远：

.. code-block:: text

    每帧位移 = 速度 × motion_blur_shutter ÷ fps

性能与限制
--------------

渲染开销正比于 ``fps × motion_blur_samples × 帧数``，
每增加一个样本就要把可见场景完整渲染一遍：

- 只有画面里确实存在开启模糊的物件时才会进入多采样流程；
  没有任何物件开启模糊（或 ``motion_blur`` 全局开关关闭）时，渲染路径与原来完全一致；
- ``motion_blur_samples=1`` 或 ``motion_blur_shutter=0`` 时也会直接退化为普通渲染；
- 预览与导出的帧率不同（``preview_fps`` 与 ``fps``），
  在预览里看到的拖影长度与导出结果可能略有差异，以导出为准。

需要注意的限制：

- 拖影完全来自"在不同时刻重新渲染"，因此对 :class:`~.Video` 这类
  内容随时间变化的物件，也只是按样本时间取对应的一帧，并不会额外插值；

相关 API
--------------

- :meth:`~.Item.set_motion_blur` / :meth:`~.Item.is_motion_blur_enabled`：物件级开关
- :class:`~.Config` 中的 ``motion_blur``：全局总开关
- :class:`~.Config` 中的 ``motion_blur_samples``：每帧的时间样本数
- :class:`~.Config` 中的 ``motion_blur_shutter``：快门时长相对于 ``1 / fps`` 的比例
