.. _config_system:

配置系统
================

配置系统的功能围绕 :class:`~.Config` 展开。

常用配置
-----------------

:class:`~.Config` 提供了若干可配置项，包括但不限于：

- ``preview_fps``: 预览界面的帧率
- ``fps``: 导出视频的帧率

.. warning::

    预览界面的帧率 ``preview_fps`` 和导出视频的帧率 ``fps`` 是两个不同的值，
    这是考虑到部分用户可能会有“在预览时降低帧率提高渲染效率，在导出时提高帧率以获得更流畅的视频”的需求。

    顺便一提，为了在预览时提高渲染效率，还有一种策略是打开窗口左上角“功能”菜单中的“跳帧”功能。

- ``background_color``: 画面的背景颜色

.. warning::

    背景颜色在设置时不能使用类似 ``background_color='#RRGGBB'`` 的形式，应使用

    - ``background_color=Color('#RRGGBB')``

    - ``background_color=Color(BLUE)``

    等形式

- ``font``: :class:`~.Text` 类所使用的默认字体

  既可以使用单个字符串 ``'Consolas'``，也可以使用一个列表来提供多个备选字体 ``['Consolas', 'Noto Serif CJK SC']``

- ``output_dir``: 输出路径，有两种格式：

  - 不以 ``:`` 符号开头时，表示相对于工作目录的路径，例如 ``videos``

    使用场景侧重于在有复杂文件结构时，将输出文件统一放到工作目录下的 ``videos`` 文件夹

  - 以 ``:`` 符号开头时，表示相对于 Timeline 所在代码文件的路径，例如 ``:/videos``

    使用场景侧重于在有复杂文件结构时，将输出文件放到每个代码文件附近单独的位置

对于更多的配置项可以参考 :class:`~.Config` 的文档

设定配置 - 三种方法
----------------------------------

了解了上面这些配置，我们也要了解如何设置它们。

方法一 - 时间轴配置
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

最常用的做法是，将配置信息和你继承的 :class:`~.Timeline` 写在一起，例如：

.. code-block:: python

    class YourTimeline(Timeline):
        CONFIG = Config(
            preview_fps=10,
            fps=120,
            background_color=Color(PURE_GREEN)
        )

        def construct(self):
            ...

这样就可以更改 ``YourTimeline`` 在运行时的配置，调整了帧率和背景颜色。

并且，和时间轴类写在一起的配置信息，也支持继承和覆盖：

.. code-block:: python

    class AwesomeTemplate(Timeline):
        CONFIG = Config(
            preview_fps=10,
            fps=120,
            output_dir='awesome_videos',
        )

        def construct(self):
            ...

    class YourTimeline(AwesomeTemplate):
        CONFIG = Config(
            output_dir=':/local_videos'
        )

        def construct(self):
            ...

在这个例子中，子类 ``YourTimeline`` 覆盖了父类的 ``output_dir``，其余配置保留 ``AwesomeTemplate`` 中的设置，这在创建模板以及覆盖模板选项时比较实用。

方法二 - 全局配置
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在使用命令行参数时，使用 ``-c 配置名 值`` 可以修改全局配置，设定的全局配置会覆盖其它配置。

例如 ``janim write your_file.py YourTimeline -c fps 120`` 可以将本次执行时的渲染帧率设置为 120。

也可以同时修改多个配置项，例如：

.. code-block:: shell

    janim write your_file.py YourTimeline -c fps 120 -c output_dir custom_dir

这个命令会将动画以 120 的帧率输出到 ``custom_dir`` 这个指定的文件夹中。

方法三 - 局部配置
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

局部配置，指的是只在代码块的一部分应用特定的配置，例如只想在某一段代码上设置特别的字体：

.. code-block:: python

    class YourTimeline(Timeline):
        def construct(self):
            txt1 = Text('Using default font')

            with Config(font='Noto Serif CJK SC'):
                txt2 = Text('Using "Noto Serif CJK SC" font')

            txt3 = Text('Using default font again')

            group = Group(txt1, txt2, txt3).show()
            group.points.arrange(DOWN, aligned_edge=LEFT)

也就是说，使用 ``with Config(key=value):`` 可以使其所包含的代码块在指定的配置下执行内容，而不影响到外部代码块的配置。

获取配置
-----------------

这些配置在更改后一般是用来改变 JAnim 进行渲染时的一些行为，如果你需要手动获取配置项具体的值，你可以使用 ``Config.get.xxx`` 的形式，例如：

.. code-block:: python

    class YourTimeline(Timeline):
        CONFIG = Config(
            preview_fps=10,
            fps=120,
        )

        def construct(self):
            print(Config.get.preview_fps)
            print(Config.get.fps)
            print(Config.get.frame_width, Config.get.frame_height)

            print(Config.get.left_side, Config.get.right_side)
            print(Config.get.bottom, Config.get.top)

其中没有设置的属性则采用默认设置 :py:obj:`~.default_config`

.. hint::

    在这个例子中，我们输出了配置项 ``preview_fps`` ``fps`` ``frame_width`` ``frame_height`` 的值。

    但后面两行的涉及的 ``left_side`` ``right_side`` ``bottom`` ``top`` 其实并不是可以直接配置的选项，
    而是由视框大小 ``frame_width`` 和 ``frame_height`` 这一组配置所决定的，这里相当于提供了一种“衍生功能”。
