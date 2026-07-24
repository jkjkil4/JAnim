安装
============

.. important::

    JAnim 是一个动画库，运行在 Python 3.12 及更高版本上。用 JAnim 制作动画的过程需要编写 Python 程序，因此要求使用者对编程有一定的了解

安装 JAnim
--------------------------------

接下来我们介绍如何安装 JAnim，我们分为“简要说明”和“详细教程”两个版本

- 如果你对 Python 及其包管理器有一定的了解，那么“简要说明”已经足够

- 而如果你是一个刚开始了解 Python 的新人，则可能需要仔细阅读“详细教程”

.. raw:: html

    <div class="hide-tabs-border">

.. tabs::

    .. translatable-tab:: 简要说明

        只需

        .. code-block:: python

            pip install janim[gui]

        不需要其它外部依赖，安装完成后运行下方命令，即可查看内置样例进一步验证安装情况

        .. code-block:: python

            janim examples

    .. translatable-tab:: 详细教程

        由于在此之后的操作或多或少要涉及到命令行操作，希望你对命令行有一定的了解

        .. raw:: html

            <div class="detail-box">
            <details>
            <summary>

        点击展开在 Windows 中如何打开命令行的简要说明

        .. raw:: html

            </summary>

        这里我们简单介绍一下打开命令行的方式，以后不再指出。在 Windows 上推荐使用自带的 Powershell，
        ❶简单的打开方式是 “Win 徽标键 + R” 打开 “运行” 窗口，输入 ``powershell`` （Powershell 7.x 需要输入 ``pwsh``），
        ❷也可以在开始菜单中输入“powershell”然后回车，
        或者❸在 VS Code 中按下 ``ctrl + ```。在 macOS / Linux 上一般是右键选择“终端”或者找到自带的终端图标。

        .. raw:: html

            </details>
            </div>

        以下简单介绍几种常见的安装方法：

        .. tabs::

            .. translatable-tab:: uv + 虚拟环境

                `uv <https://github.com/astral-sh/uv>`_ 是一套用于 Python 项目管理的工具链，目前已经相对完善，对于需要频繁使用 Python 多版本和多依赖库的开发者来说很方便。官方提供了很多安装方法，可以使用包管理工具安装，也可以独立安装。

                .. note::

                    如果你对使用 ``uv`` 还不熟悉并略有困惑，可以 **点击上面分页中的 “Python + 全局” 切换到更为经典的安装方式**，这样你可能会更容易理解，但我们仍然推荐使用 ``uv`` 进行管理

                首先可以在命令行中粘贴以下脚本安装 ``uv``

                .. tabs::

                    .. translatable-tab:: Windows

                        .. code-block:: bash

                            powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

                    .. translatable-tab:: macOS 或 Linux

                        .. code-block:: bash

                            curl -LsSf https://astral.sh/uv/install.sh | sh

                        如果你的系统中没有 ``curl``，则可以使用 ``wget``：

                        .. code-block:: bash

                            wget -qO- https://astral.sh/uv/install.sh | sh

                本节介绍每个文件夹下创建独立虚拟环境的方式。假如你在一个适当的文件路径（以下用 “/my/path” 指代）下，想在一个叫 “janim-folder” 的文件夹下集中开发，那么请逐行运行以下命令，它会自动创建 “janim-folder” 并在其中创建虚拟环境。

                .. code-block:: bash

                    cd "/my/path"
                    uv init "janim-folder"
                    cd "janim-folder"
                    uv add janim[gui]
                    uv run janim --version  # 看到版本号说明安装完成

                用这种方式安装后，文档中所有 ``janim`` 指令都要换成 ``uv run janim``，如果仍然要直接调用 ``janim``，则需要先 `激活虚拟环境 <https://docs.astral.sh/uv/pip/environments/#using-a-virtual-environment>`_，这是出于全局和本项目隔离的目的。

                .. tip::

                    一切就绪后，可以使用 ``uv run janim examples`` 查看内置示例，进一步检验 JAnim 的安装情况
                
            .. translatable-tab:: uv + 全局

                `uv <https://github.com/astral-sh/uv>`_ 是一套用于 Python 项目管理的工具链，目前已经相对完善，对于需要频繁使用 Python 多版本和多依赖库的开发者来说很方便。官方提供了很多安装方法，可以使用包管理工具安装，也可以独立安装。

                .. note::

                    如果你对使用 ``uv`` 还不熟悉并略有困惑，可以 **点击上面分页中的 “Python + 全局” 切换到更为经典的安装方式**，这样你可能会更容易理解，但我们仍然推荐使用 ``uv`` 进行管理

                首先可以在命令行中粘贴以下脚本安装 ``uv``

                .. tabs::

                    .. translatable-tab:: Windows

                        .. code-block:: bash

                            powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

                    .. translatable-tab:: macOS 或 Linux

                        .. code-block:: bash

                            curl -LsSf https://astral.sh/uv/install.sh | sh

                        如果你的系统中没有 ``curl``，则可以使用 ``wget``：

                        .. code-block:: bash

                            wget -qO- https://astral.sh/uv/install.sh | sh

                和在虚拟环境中安装不同的是，全局安装不需要指定用来开发项目的文件夹。

                .. code-block:: bash

                    uv tool install janim[gui]
                    janim --version     # 看到版本号说明安装完成

                .. tip::

                    一切就绪后，可以使用 ``janim examples`` 查看内置示例，进一步检验 JAnim 的安装情况

            .. translatable-tab:: Python + 全局

                Python 可以直接安装，而且多版本可以共存。访问 `Python 官网下载页 <https://www.python.org/downloads/>`_ 选择 3.12 或更高版本，下载安装。

                使用 Python 自带的 ``pip`` 工具，会自动将依赖安装在全局。打开命令行输入该命令即可：

                .. code-block:: bash

                    pip install janim[gui]
                    janim --version     # 看到版本号说明安装完成

                .. tip::

                    一切就绪后，可以使用 ``janim examples`` 查看内置示例，进一步检验 JAnim 的安装情况
            
            .. translatable-tab:: Conda (TODO)

                有待完善，欢迎补充

.. raw:: html

    </div>

可能出现的安装问题
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. raw:: html

    <div class="detail-box">

.. raw:: html

    <details>
    <summary>Microsoft Visual C++ 14.0 or greater is required.</summary>

安装时， ``glcontext`` 包出现以下报错：

.. code-block::

    error: Microsoft Visual C++ 14.0 or greater is required. Get it with "Microsoft C++ Build Tools":
    https://visualstudio.microsoft.com/visual-cpp-build-tools/

只需要按照他给出的链接 https://visualstudio.microsoft.com/visual-cpp-build-tools/ 下载，然后进行安装。

在安装组件时勾选 **“使用 C++ 的桌面开发”** 后点击安装按钮，如下图

.. image:: /_static/images/VCpp.png

安装完成后再次尝试安装 ``JAnim`` 即可。

如果仍然失败，可以尝试重启终端、编辑器，或者重启电脑后再次尝试。

.. raw:: html

    </details>

.. raw:: html

    </div>

.. _install-dep:

额外依赖项
-------------------

JAnim 运作并不依赖外部程序，但是在一些少见的情况中，你可能需要安装一些额外依赖

在缺少某些额外依赖项的情况下，JAnim 会给出提醒，因此在使用时不必担心，可以在遇到提示后，重新访问该页面检查

以下列出了可能遇到的情况：

.. raw:: html

    <div class="detail-box">

.. raw:: html

    <details>
    <summary>

JAnim 导出 ``.mp4`` 视频时不需要外部程序，但是如果你想要尝试硬件加速，则需要安装 FFmpeg

.. raw:: html

    </summary>

当你运行类似这样的命令行时

.. code-block:: bash

    janim write ... ... --hwaccel

可能会得到报错，提示需要安装 FFmpeg，你可以参考以下安装方式：

.. tabs::

    .. translatable-tab:: Windows + 使用包管理器（推荐）

        在 Windows 系统中，一般来说会自带一个 ``Winget``，使用以下命令即可安装

        .. code-block:: bash

            winget install ffmpeg 

        安装后，你需要重新命令行或 VSCode， ``ffmpeg`` 才能够正常使用，可使用以下命令检查

        .. code-block:: bash

            ffmpeg --version    # 输出版本号则安装成功

        如果无法使用或是对其它包管理器有所偏好，可以另行参考 `Chocolatey <https://community.chocolatey.org/>`_ 或者 `Scoop <https://scoop.sh/>`_，或是 `UniGetUI <https://github.com/marticliment/UniGetUI>`_ 图形化界面

    .. translatable-tab:: Windows + 直接下载二进制

        直接下载二进制文件，需要手动处理安装位置、添加环境变量、更新二进制的问题

        可以访问 https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z 下载压缩包，解压到合适的位置，并配置环境变量，这里不展开赘述

    .. translatable-tab:: macOS

        推荐使用包管理器安装，这里使用常见的 `Homebrew <https://brew.sh/>`_ 作为示例

        Homebrew 是 macOS 上最常用的包管理器，使用下面这个命令即可安装（如果你已经安装过了，可以跳过）：

        .. code-block:: bash

            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        接着便可以使用 Homebrew 安装 FFmpeg

        .. code-block:: bash

            brew install ffmpeg
            ffmpeg --version    # 输出版本号则安装成功

    .. translatable-tab:: Linux

        考虑到使用 `类 UNIX <https://zh.wikipedia.org/wiki/%E7%B1%BBUnix%E7%B3%BB%E7%BB%9F>`_ 的用户一般对命令行更有了解，
        而且相应的发行版多，包管理没有通用的命令，这里仅给出在 Ubuntu 中的安装方法

        .. code-block:: bash

            sudo apt update
            sudo apt install ffmpeg
            ffmpeg --version    # 输出版本号则安装成功
        
        不同发行版包管理器不同，请自行适配

.. raw:: html

    </details>

.. raw:: html

    <details>
    <summary>

对于 Linux 系统，如果需要在预览界面中正常播放音频，则需要安装 ``PortAudio``

.. raw:: html

    </summary>

在 Linux 系统中，当你在预览界面中播放带有音频的 :class:`~.Timeline` 时，可能会遇到需要安装 ``pip install sounddevice`` 的提示

而这个库在 Linux 系统上还需要额外的依赖 ``PortAudio``

考虑到使用 `类 UNIX <https://zh.wikipedia.org/wiki/%E7%B1%BBUnix%E7%B3%BB%E7%BB%9F>`_ 的用户一般对命令行更有了解，
而且相应的发行版多，包管理没有通用的命令，这里仅给出在 Ubuntu 中的安装方法

.. code-block:: bash

    sudo apt update
    sudo apt install portaudio19-dev

不同发行版包管理器不同，请自行适配

.. raw:: html

    </details>


.. raw:: html

    </div>

安装 VS Code
------------

推荐使用 `VS Code <https://code.visualstudio.com/>`_ 进行开发，这样可以通过其中的 ``janim-toolbox`` 插件让 JAnim 的使用更加方便

具体可以参考 :ref:`VS Code 插件 <vscode_extension>` 中的介绍

----

.. tip::

    请点击页面的右下角的按钮进入下一节，在之后的小节中不再赘述
