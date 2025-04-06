安装
============

.. important::

    JAnim 是一个动画库，运行在 Python 3.12 及更高版本上。用 JAnim 制作动画的过程需要编写 Python 程序，因此要求使用者对编程有一定的了解

步骤
~~~~~~~~

.. _install_dep:

安装依赖项
------------

以下依赖需要全局安装在系统中：

- `FFmpeg <https://ffmpeg.org>`_ （用于输出视频文件，在 Windows 下安装需要配置 **环境变量**）
- `Typst <https://github.com/typst/typst/releases>`_ （可选，用于公式排版，需要配置 **环境变量**）

.. tabs::

    .. tab:: Windows + 使用包管理器（推荐）

        Windows 系统的包管理不一定是开箱即用的，通常需要略微熟悉命令行操作并且需要少量配置。这个配置过程相对来说比较费时，但是一旦配置好就能自动处理很多琐事。笔者此处推荐使用包管理器。

        包管理器有很多选择，一般来说 Windows 应该自带一个 Winget，也可以使用 `Chocolatey <https://community.chocolatey.org/>`_ 或者 `Scoop <https://scoop.sh/>`_。三者只需安装一种，不过多装的话也没什么冲突。

        安装完包管理器（或者自带 Winget），以 Winget 为例，按 ``Win + R`` 输入 ``powershell`` 或者在开始菜单中输入 powershell 打开 Powershell，输入 ``winget install typst`` 以及 ``winget install ffmpeg`` 即可完成安装。其他两种也是同理。

        .. tip::

            如果不熟悉命令行，希望使用图形化界面，也可以安装 `UniGetUI <https://github.com/marticliment/UniGetUI>`_ 来对包管理器进行统一展示和调用，注意它只是包管理器的图形界面，仍然需要环境中存在对应包管理器才能使用

    .. tab:: Windows + 直接下载二进制

        直接下载二进制文件，需要的环节更少，但是需要手动处理安装位置、添加环境变量、更新二进制的问题。

        首先安装 FFmpeg。点击 https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z 下载压缩包，解压，将 ``ffmpeg-`` 开头的文件夹移到适当的位置（例如 ``C:\\Program Files``），把该文件夹改名为 ``ffmpeg``。

        然后安装 Typst。点击 https://github.com/typst/typst/releases/latest/download/typst-x86_64-pc-windows-msvc.zip 下载压缩包（如果网络错误可以反复尝试几次），解压，将 ``typst-x86_64-pc-windows-msvc`` 移到适当的位置，把该文件夹改名为 ``typst``。

        最后添加环境变量。如果使用的是 Windows 11，可以按“Windows 徽标”键或者点击“开始”按钮，输入“环境变量”。（如果使用之前的版本可以右键此电脑 - 属性 - 高级系统设置）。点击“环境变量”，双击“用户变量”（或“系统变量”，任选其一）的“Path”，右键刚刚的 ``typst`` 文件夹并“复制文件地址”，在 Path 窗口（如下图）点击“新建”并把文件地址粘贴进去（注意不要带引号）。类似操作，将 ``ffmpeg\bin`` 也就是刚刚得到的 ffmpeg 下的 bin 文件夹的文件地址粘贴进去。

        .. image:: /_static/images/envedit.png
            :align: center
            :scale: 80%

        尝试一下有没有正确识别。在“开始”菜单输入并打开 PowerShell 或者 Cmd，运行 ``ffmpeg --version`` 和 ``typst --version``，输出版本号则安装成功。

    .. tab:: macOS

        推荐使用包管理器安装，这里使用常见的 `Homebrew <https://brew.sh/>`_ 作为示例。

        Homebrew 是 macOS 上最常用的包管理器，使用下面这个命令即可安装（如果你已经安装过了，可以跳过）：

        .. code-block:: bash

            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        接着便可以使用 Homebrew 安装 FFmpeg 和 Typst

        .. code-block:: bash

            # FFmpeg
            brew install ffmpeg
            ffmpeg --version    # 输出版本号则安装成功

            # Typst
            brew install typst
            typst --version     # 输出版本号则安装成功

        另外，在 macOS 上使用 JAnim 窗口还需要安装 portaudio

        .. code-block:: bash

            brew install portaudio
            brew link portaudio     # 可能需要执行这条命令，通常情况下是已经链接好的，只是以防万一

        使用 ``brew --prefix portaudio`` 命令查看 portaudio 的安装路径，记下这个路径，后面会用到。（例：在笔者设备上查看的结果是 ``/opt/homebrew/opt/portaudio``）

        在用户主目录（``/Users/你的用户名/``` 或者等价的 ``~``）下创建 .pydistutils.cfg 配置文件，根据我们刚刚记下的路径，添加 include 路径和 lib 路径并保存，例如在笔者设备上创建的文件内容如下图红框所示：

        .. image:: /_static/images/portaudio_pydist.png
            :align: center

        接下来便可以按照后面的教程安装 JAnim 了，如果在安装 JAnim 时遇到 portaudio 的问题，可以再来检查一下上述路径是否配置正确

    .. tab:: Linux

        考虑到使用 `类 UNIX <https://zh.wikipedia.org/wiki/%E7%B1%BBUnix%E7%B3%BB%E7%BB%9F>`_ 的用户一般对命令行更有了解，而且相应的发行版多，包管理没有通用的命令。这里仅给出 Ubuntu 的安装方法。

        打开终端，运行以下命令。FFmpeg 使用包管理器安装，不同发行版包管理器不同，请自行适配。

        .. code-block:: bash

            # FFmpeg
            sudo apt update
            sudo apt install ffmpeg
            ffmpeg --version    # 输出版本号则安装成功

        Typst 由于相对较新且未进入稳定版，直接从源代码仓库下载安装。

        .. code-block:: bash

            # Typst （参考 https://lindevs.com/install-typst-on-ubuntu）
            wget -qO typst.tar.xz https://github.com/typst/typst/releases/latest/download/typst-x86_64-unknown-linux-musl.tar.xz
            sudo tar xf typst.tar.xz --strip-components=1 -C /usr/local/bin typst-x86_64-unknown-linux-musl/typst
            typst --version     # 输出版本号则安装成功
            rm -rf typst.tar.xz

        笔者仅在一台虚拟机上尝试过以上安装，不保证真实环境也能做到。网络波动、本地命令不存在、文件重名等等原因都可能导致安装失败。有安装问题请在 GitHub 或群聊中及时提出并附带错误信息和/或截图。

安装 JAnim
---------------------------

JAnim 是一个库并且提供了可以直接调用的二进制，熟悉 Python 库的开发者可以自行选用合适的方法安装。整体上来说有两种安装思路，各有优势。安装在全局的好处是所有项目都可以调用同一套库，可以直接调用命令而不需要先切换环境和目录；安装在虚拟环境的好处是做到项目间的依赖隔离，并且不会污染全局的指令。

以下简单介绍几种常见的安装方法。由于在此之后的操作或多或少要涉及到命令行操作，所以简单介绍一下打开命令行的方式，以后不再指出。在 Windows 上推荐使用自带的 Powershell，❶简单的打开方式是 “Win 徽标键 + R” 打开 “运行” 窗口，输入 ``powershell`` （Powershell 7.x 需要输入 ``pwsh``），❷也可以如上所说在开始菜单中输入“powershell”然后回车，或者❸在 VS Code 中按下 ``ctrl + ```。在 macOS / Linux 上一般是右键选择“终端”或者找到自带的终端图标。

.. tabs::

    .. tab:: uv + 虚拟环境

        `uv <https://github.com/astral-sh/uv>`_ 是一套用于 Python 项目管理的工具链，目前已经相对完善，对于需要频繁使用 Python 多版本和多依赖库的开发者来说很方便。官方提供了很多安装方法，可以用上文提到的包管理工具安装，也可以独立安装。

        .. note::

            这一条目借鉴了 `manimCE 项目的安装文档 <https://docs.manim.community/en/stable/installation/uv.html>`_，命令行安装 ``uv`` 以及进一步新建项目的命令都可以参考其中相应段落

            如果你对使用 ``uv`` 还不熟悉并略有困惑，可以点击上面分页中的 “Python + 全局” 切换到更为经典的安装方式，这样你可能会更容易理解，但我们仍然推荐使用 ``uv`` 进行管理

        本节介绍每个文件夹下创建独立虚拟环境的方式。假如你在一个适当的文件路径（以下用 “/my/path” 指代）下，想在一个叫 “JAnim-folder” 的文件夹下集中开发，那么请逐行运行以下命令，它会自动创建 “JAnim-folder” 并在其中创建虚拟环境。

        .. code-block:: bash

            cd "/my/path"
            uv init "JAnim-folder"
            cd "JAnim-folder"
            uv add janim[gui]
            uv run janim --version  # 看到版本号说明安装完成

        用这种方式安装后，文档中所有 ``janim`` 指令都要换成 ``uv run janim``，如果仍然要直接调用 ``janim``，则需要先 `激活虚拟环境 <https://docs.astral.sh/uv/pip/environments/#using-a-virtual-environment>`_，这是出于全局和本项目隔离的目的。

        .. tip::

            一切就绪后，可以使用 ``uv run janim examples`` 查看内置示例，进一步检验 JAnim 以及依赖项的安装情况

    .. tab:: uv + 全局

        `uv <https://github.com/astral-sh/uv>`_ 是一套用于 Python 项目管理的工具链，目前已经相对完善，对于需要频繁使用 Python 多版本和多依赖库的开发者来说很方便。官方提供了很多安装方法，可以用上文提到的包管理工具安装，也可以独立安装。

        .. note::

            这一条目借鉴了 `manimCE 项目的安装文档 <https://docs.manim.community/en/stable/installation/uv.html>`_，命令行安装 ``uv`` 以及进一步新建项目的命令都可以参考其中相应段落

            如果你对使用 ``uv`` 还不熟悉并略有困惑，可以点击上面分页中的 “Python + 全局” 切换到更为经典的安装方式，这样你可能会更容易理解，但我们仍然推荐使用 ``uv`` 进行管理

        和在虚拟环境中安装不同的是，全局安装不需要指定用来开发项目的文件夹。

        .. code-block:: bash

            uv tool install janim[gui]
            janim --version     # 看到版本号说明安装完成

        .. tip::

            一切就绪后，可以使用 ``janim examples`` 查看内置示例，进一步检验 JAnim 以及依赖项的安装情况

    .. tab:: Python + 全局

        Python 可以直接安装，而且多版本可以共存。访问 `Python 官网下载页 <https://www.python.org/downloads/>`_ 选择 3.12 或更高版本，下载安装。

        使用 Python 自带的 pip 工具，会自动将依赖安装在全局。打开命令行输入该命令即可：

        .. code-block:: bash

            pip install janim[gui]
            janim --version     # 看到版本号说明安装完成

        .. tip::

            一切就绪后，可以使用 ``janim examples`` 查看内置示例，进一步检验 JAnim 以及依赖项的安装情况

    .. tab:: Conda + 全局（TODO）

        有待完善，欢迎补充

.. _install_vscode:

安装 VS Code
------------

推荐使用 `VS Code <https://code.visualstudio.com/>`_ 进行开发，GUI 的布局是为之适配的

.. tip::

    请点击页面的右下角的按钮进入下一节，在之后的小节中不再赘述
