.. janim documentation master file, created by
   sphinx-quickstart on Tue Dec 26 23:12:20 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

JAnim 文档
=================================

JAnim 是一个用于创建流畅动画的库，以程序化动画为核心理念，并支持实时编辑、实时预览，并支持更多其它丰富的功能。

以下是一部分样例展示（注：可以直接点击分页标题快速折叠这部分内容）

.. tabs::

   .. translatable-tab:: 基础样例

      .. random-choice::

         .. include:: examples/_basic_examples_options.rst

   .. translatable-tab:: 类 Slide 演示

      .. random-choice::
         :start-text: 🎲 点击“随机切换”显示一个样例
         :destroy:

         .. include:: examples/_slide_examples_options.rst

   .. translatable-tab:: 自动化解析与生成

      .. random-choice::
         :start-text: 🎲 点击“随机切换”显示一个样例
         :destroy:

         .. include:: examples/_auto_examples_options.rst

   .. translatable-tab:: 视频叠加动画

      .. random-choice::
         :start-text: 🎲 点击“随机切换”显示一个样例
         :destroy:

         .. include:: examples/_note_examples_options.rst

.. toctree::
   :maxdepth: 1
   :caption: 安装并快速上手

   installation
   get_started

如果你在安装时遇到困难，或是在使用时有任何问题，可以在 Github 的 `Discussions 页面 <https://github.com/jkjkil4/JAnim/discussions>`_ 提问，或加入 QQ 群 970174336

.. toctree::
   :maxdepth: 1
   :caption: 基础教程 - 了解基本概念

   tutorials/coordinates
   tutorials/bounding_box
   tutorials/animations
   tutorials/item_group
   tutorials/config_system
   tutorials/updaters

.. toctree::
   :maxdepth: 1
   :caption: 界面教程 - 使用 JAnim GUI

   tutorials/use_gui
   tutorials/gui_commands

.. toctree::
   :maxdepth: 1
   :caption: 资源教程 - 使用外部素材

   tutorials/insert_assets
   tutorials/audio_and_subtitle

.. toctree::
   :maxdepth: 1
   :caption: 进阶教程 - 掌握更多实用机制

   tutorials/typst_usage
   tutorials/value_tracker
   tutorials/sub_timeline
   tutorials/camera_usage
   tutorials/3d_scene

.. toctree::
   :maxdepth: 1
   :caption: 其它教程

   tutorials/geometry_reshape
   tutorials/group_advanced_usage
   tutorials/depth_detail
   tutorials/essence_of_points

.. toctree::
   :maxdepth: 1
   :caption: 其它

   other/guide_for_manim_users
   other/faq

.. toctree::
   :maxdepth: 1
   :caption: 样例索引

   examples/basic_examples
   examples/slide_examples
   examples/auto_examples
   examples/note_examples

.. toctree::
   :maxdepth: 2
   :caption: 参考文档

   janim/modules

.. toctree::
   :caption: 开发相关
   :maxdepth: 1

   development/about
   development/contributing
   development/unittest
   development/bench

目录与表格
------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
