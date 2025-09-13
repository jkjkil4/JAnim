字幕与配音
===============================

插入音频
-------------------------------

JAnim 支持插入音频，并在导出时合并到视频中：

.. code-block:: python

    audio = Audio('audio.mp3')
    self.play_audio(audio)

默认情况下，音频会在当前时刻开始播放；关于播放音频的具体细节请参考 :meth:`~.Timeline.play_audio` 方法。

利用时段信息进行同步
-------------------------------

:meth:`~.Timeline.play_audio` 方法还会返回一个 :class:`~.TimeRange` 对象，使得这样成为可能：

.. code-block:: python

    audio1 = Audio('audio1.mp3')
    t = self.play_audio(audio1)
    self.forward(t.duration)

    txt = Text('This text is written as the audio plays')

    audio2 = Audio('audio2.mp3')
    t = self.play_audio(audio2)
    self.play(Write(txt), duration=t.duration)

也就是说，通过获知音频的时段信息，例如这里的时长，可以进行如同步音频与动画等各种灵活的操作。

JAnim 也可以通过 :meth:`~.Timeline.subtitle` 方法插入字幕，并与音频同步：

.. code-block:: python

    self.forward()

    audio = Audio('audio.mp3')
    t = self.play_audio(audio)
    self.subtitle('This is a subtitle', duration=t.duration)
    self.forward_to(t.end)

    self.forward()

关于字幕的具体细节请参考 :meth:`~.Timeline.subtitle` 方法。

.. tip::

    :meth:`~.Timeline.subtitle` 同样会返回一个 :class:`~.TimeRange` 对象，提供了字幕的时段信息。

插入字幕及其配音的简便方法
-------------------------------

如果你想要插入一段字幕及其配音，可以使用 :meth:`~.Timeline.audio_and_subtitle` 方法，这是对 :meth:`~.Timeline.play_audio` 和 :meth:`~.Timeline.subtitle` 的封装：

.. code-block:: python

    t = self.aas('audio.mp3', 'This is a subtitle')
    self.forward(t.duration)

.. tip::

    :meth:`~.Timeline.audio_and_subtitle` 可以简写为 :meth:`~.Timeline.aas`。

.. important::

    :meth:`~.Timeline.audio_and_subtitle` 方法默认会自动去除音频前后多余的空白，可以传入 ``clip=None`` 以禁用，或是使用 ``clip=(start, end)`` 来手动确定裁剪区段。
