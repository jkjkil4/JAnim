为程序国际化作出贡献
==========================

.. note::

    对于程序国际化而言，英文（en）和中文（zh_CN）是良好维护的，
    如果你有需要给程序提供到其它语言的翻译，可以考虑进一步阅读这一部分

    否则，你可以略过程序国际化的这部分

生成翻译文件
-------------------

请确保安装了 `GNU gettext <https://www.gnu.org/software/gettext/>`_

.. note::

    翻译流程可参考 `<https://www.sphinx-doc.org/en/master/usage/advanced/intl.html>`_

1. 提取可翻译的文本

在项目的根目录执行：

.. code-block:: sh

    python janim/locale/gettext.py

这个命令会对项目内的所有 .py 文件执行 xgettext，如果有可翻译的文本，则会提取到 ``janim/locale/source`` 文件夹内，产生（或更新）.pot 文件

2. 产生 .po 文件

pot 文件是提取出来的可供翻译的源语言文字，你还需要使用这些文件来产生对应语言的 po 文件

举个例子

.. code-block:: sh

    python janim/locale/intl.py ja

执行后，产生的 po 文件会输出到以下文件夹中

- ``janim/locale/ja/LC_MESSAGES/``

其中 ``ja`` 对应上面命令中所提供的参数，表示日语

进行程序翻译
------------------

假设你要进行翻译到日语的工作

现在 ``janim/locale/ja/LC_MESSAGES/`` 中已经存放了翻译文件（后缀 ``.po``）

这里推荐使用 Poedit 软件，打开目录内的 po 文件，进行翻译

翻译后，提交你的更改，创建合并到 ``main`` 分支的 Pull Request
