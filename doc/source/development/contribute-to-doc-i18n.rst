为文档国际化作出贡献
===========================

.. note::

    已有的文档

    - zh_CN: https://janim.readthedocs.io/zh-cn/latest/
    - en: https://janim.readthedocs.io/en/latest/

.. _generate-po:

生成翻译文件
-------------------

.. note::

    大多数情况下，翻译文件（后缀 ``.po``）已经生成到了项目中，
    如果你只是想编辑已有的翻译文件，可以跳过 :ref:`generate-po` 这段，直接到 :ref:`do-translate` 便可以开始翻译

.. warning::

    我只知道在 Windows 和 MacOS 中，以下步骤有效

    欢迎测试在其它系统中的有效性或补充对应的方法

.. note::

    翻译流程可参考 `<https://www.sphinx-doc.org/en/master/usage/advanced/intl.html>`_

1. 安装必要环境

假设你已经 fork 仓库并 clone 到了本地

使用 ``cd JAnim`` 进入项目文件夹：

接着，使用以下命令安装必要的环境：

.. code-block:: sh

    pip install -e .[gui,doc]
    pip install sphinx-intl

2. 提取翻译文本

.. code-block:: sh

    cd doc

进入 ``doc/`` 文件夹，并使用

.. code-block:: batch

    ./make gettext

或（在 MacOS 中）

.. code-block:: sh

    make gettext

提取可翻译的文本，产生的 pot 文件会输出到 ``doc/build/gettext/`` 中

3. 产生 po 文件

pot 文件是提取出来的可供翻译的源语言文字，你还需要使用这些文件来产生对应语言的 po 文件

.. code-block:: sh

    sphinx-intl update -p build/gettext -l de -l ja

执行后，产生的 po 文件会输出到以下文件夹中

- ``doc/source/locales/de/LC_MESSAGES/``
- ``doc/source/locales/ja/LC_MESSAGES/``

其中 ``de`` 和 ``ja`` 分别对应上面命令中所提供的参数

.. note::

    这里的 ``de`` 表示德语， ``ja`` 表示日语，表明你想要进行对这些语言的翻译工作

    比如，如果你想要进行翻译到英文的工作，那么执行

    .. code-block:: sh

        sphinx-intl update -p build/gettext -l en

    则会在 ``doc/source/locales/en/LC_MESSAGES/`` 中产生可翻译的文件

.. _do-translate:

进行文档翻译
----------------------

假设你要进行翻译到英文的工作

现在 ``doc/source/locales/en/LC_MESSAGES/`` 中已经存放了翻译文件（后缀 ``.po``）

这里推荐使用 Poedit 软件，打开目录内的 po 文件，进行翻译

.. note::

    如果你有能力检查的话，使用 GPT 翻译也无妨（但是记得校对哦）

.. note::

    .. code-block::

        基类：:py:class:`......`

    对于类似这样的翻译文本，可以直接忽略，或者将其完全复制到结果中

    因为这个其实是不需要手动翻译的

翻译后，提交你的更改，创建合并到 ``main`` 分支的 Pull Request

在本地构建文档
----------------------

.. note::

    别忘了安装必要的环境

    .. code-block:: sh

        pip install -e .[gui,doc]

.. tabs::

    .. tab:: Windows

        首先确保你在 ``doc/`` 目录下：

        .. code-block:: batch

            cd doc

        举个例子，如果你想要在本地构建 zh_CN（简体中文）的文档，可以执行：

        .. code-block:: batch

            .\make_i18n zh_CN

        这样就会在 ``build/html_i18n/zh_CN`` 下生成网页文件，点击其中的 ``index.html`` 即可打开

        其它的语言同理，把 ``zh_CN`` 改成对应的语言代码就好了

    .. tab:: MacOS

        首先确保你在 ``doc/`` 目录下：

        .. code-block:: sh

            cd doc

        举个例子，如果你想要在本地构建 zh_CN（简体中文）的文档，可以执行：

        .. code-block:: sh

            ./make_i18n.sh zh_CN

        这样就会在 ``build/html_i18n/zh_CN`` 下生成网页文件，点击其中的 ``index.html`` 即可打开

        其它的语言同理，把 ``zh_CN`` 改成对应的语言代码就好了

    .. tab:: Linux

        .. warning::

            以下方法未在 Linux 上测试，欢迎测试在 Linux 中的有效性或补充对应的方法

        首先确保你在 ``doc/`` 目录下：

        .. code-block:: sh

            cd doc

        举个例子，如果你想要在本地构建 zh_CN（简体中文）的文档，可以执行：

        .. code-block:: sh

            ./make_i18n.sh zh_CN

        这样就会在 ``build/html_i18n/zh_CN`` 下生成网页文件，点击其中的 ``index.html`` 即可打开

        其它的语言同理，把 ``zh_CN`` 改成对应的语言代码就好了
