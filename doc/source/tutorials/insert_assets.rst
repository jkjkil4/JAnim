插入外部素材
======================

.. raw:: html

    <div class="page-insert_assets">

JAnim 支持通过 :class:`~.ImageItem` 、 :class:`~.VideoFrame` 和 :class:`~.Video` 插入图片或视频，也可以使用 :class:`~.SVGItem` 解析 SVG 矢量图。

插入图像/截取视频帧
----------------------------

:class:`~.ImageItem` 插入的图片默认以原始尺寸转换到 JAnim 坐标系中显示，可以传入 ``width`` 和 ``height`` 参数指定显示尺寸。

``width`` 和 ``height`` 参数表示在 JAnim 坐标系中的尺寸，如果只指定其中一个参数，另一个参数会按照图片的原始宽高比自动计算，亦即，会保持图片的宽高比不变。

:class:`~.VideoFrame` 会截取视频在指定时刻的画面，作为图像插入，其它参数与 :class:`~.ImageItem` 一致。

插入视频
---------------------

可使用 :class:`~.Video` 插入视频，参数设置与 :class:`~.ImageItem` 基本一致。

还支持使用 ``loop`` 参数控制是否循环播放（对于 ``.gif`` 格式会比较实用），使用 ``frame_components=4`` 插入带透明通道的视频（如 ``.mov`` 视频）。

具体用法请参考 :class:`~.Video` 文档。

插入 SVG 矢量图
---------------------

:class:`~.SVGItem` 可解析 SVG 矢量图，将其转化为 JAnim 物件组。

.. raw:: html

    </div>
