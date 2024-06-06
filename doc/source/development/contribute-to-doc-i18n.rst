为文档国际化作出贡献
===========================

.. note::

    已有的文档

    - zh_CN: https://janim.readthedocs.io/zh-cn/latest/
    - en: https://janim.readthedocs.io/en/latest/

.. _generate-po:

生成翻译文件
-------------------

.. warning::

    大多数情况下，翻译文件（后缀 ``.po``）已经生成到了项目中，
    如果你只是想编辑已有的翻译文件，可以跳过 :ref:`generate-po` 这段，直接到 :ref:`do-translate` 便可以开始翻译

.. warning::

    我只知道在 Windows 中，以下步骤有效

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

使用

.. code-block:: sh

    cd doc

进入 ``doc/`` 文件夹，并使用

.. code-block:: sh

    ./make gettext

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

翻译后，提交你的更改，创建合并到 ``main`` 分支的 Pull Request

在本地构建文档
----------------------

.. note::

    TODO
