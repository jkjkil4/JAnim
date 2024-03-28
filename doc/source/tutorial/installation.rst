安装
============

~~~

.. important::

    JAnim 运行在 Python 3.12 及更高版本

    并且需要 OpenGL 4.3 及更高版本

安装 Python
------------

访问 `Python 官网下载页 <https://www.python.org/downloads/>`_ 下载 3.12 或更高版本

.. _install_dep:

安装依赖项
------------

所需的系统依赖有：

- `FFmpeg <https://ffmpeg.org>`_ （Windows 下安装需要配置 **环境变量**）
- `typst <https://github.com/typst/typst/releases>`_ （可选，如果需要公式排版则必须，需要配置 **环境变量**）

使用 Python 环境安装 JAnim
---------------------------

.. code-block:: sh

    # 通过 pip 安装 JAnim
    pip install janim[gui]

    # 运行样例
    janim examples

.. _install_vscode:

安装 vscode
------------

推荐使用 `vscode <https://code.visualstudio.com/>`_ 进行开发

.. tip::

    请点击页面的右下角的按钮进入下一节，在之后的小节中不再赘述
