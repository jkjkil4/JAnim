:orphan:

贡献程序国际化
==========================

在 JAnim 中的程序国际化，包括翻译程序运行时的提示信息、错误信息、CLI 文本、GUI 界面文本等。

.. note::

    对于程序国际化而言，英文（en）和中文（zh_CN）是良好维护的。
    如果你有需要为程序提供其它语言的翻译，可以继续阅读本文档。

准备环境
-------------------

假设你已经 fork 仓库并 clone 到了本地。

使用 ``cd JAnim`` 进入项目文件夹，然后安装必要的环境：

.. code-block:: sh

    pip install -e .

另外，需要确保已安装 `GNU gettext <https://www.gnu.org/software/gettext/>`_

工作流程
-----------

程序国际化的工作流程分为以下步骤：

1. **更新翻译文件**：提取最新的可翻译文本并生成/更新 .po 文件
2. **进行翻译**：编辑 .po 文件进行翻译
3. **编译翻译文件**：将 .po 文件编译为 .mo 文件（仅在必要时）

.. _update-po-files-code:

更新翻译文件
-------------------

要创建新语言的翻译或更新现有翻译文件，使用以下命令：

.. code-block:: sh

    python scripts update-po code <language>

其中 ``<language>`` 是你要翻译的语言代码（例如 ``ja`` 表示日语， ``de`` 表示德语等）。

.. note::

    ``en`` 是程序文本的源语言，因此不需要为其创建翻译文件。

.. 该命令会执行以下步骤：

.. - 扫描项目中所有 Python 文件，提取所有需要翻译的字符串（使用 ``_('...')`` 标记）
.. - 将提取的字符串放入 ``.pot`` 模板文件（在 ``janim/locale/source/`` 目录中）
.. - 从 ``.pot`` 文件生成或更新相应语言的 ``.po`` 文件（在 ``janim/locale/<language>/LC_MESSAGES/`` 目录中）

完成后，你可以在相应的 ``janim/locale/<language>/LC_MESSAGES/`` 目录中找到所有的 ``.po`` 文件。

检查翻译完成情况
-------------------

在开始翻译或翻译过程中，你可以检查翻译的完成情况：

.. code-block:: sh

    python scripts check-po code <language>

该命令会扫描所有 ``.po`` 文件，并列出仍有未翻译（untranslated）或模糊（fuzzy）条目的文件。
这有助于你了解还需要进行哪些翻译工作。

并且一些软件，比如 Poedit 的编目管理器也可以列出文件夹中的 ``.po`` 文件的翻译完成情况。

进行程序翻译
-------------------

现在 ``janim/locale/<language>/LC_MESSAGES/`` 中已经存放了翻译文件（后缀 ``.po``）。

可以使用 Poedit 软件来编辑 ``.po`` 文件，或者用任何文本编辑器直接编辑。

完成翻译后，提交你的更改，创建合并到 ``main`` 分支的 Pull Request。

编译翻译文件（仅在必要时）
----------------------------

如果你是使用 Poedit 等软件编辑，多半会在编辑后自动编译产生 ``.mo`` 文件。
但如果你是直接使用文本编辑器编辑的 ``.po`` 文件，需要手动编译 ``.po`` 文件为 ``.mo`` 文件，可以使用：

.. code-block:: sh

    python scripts compile-po code <language>

完整操作示例
-------------------

假设你要为程序提供日语翻译，完整流程如下：

1. 更新翻译文件：

   .. code-block:: sh

       python scripts update-po code ja

2. 编辑 ``janim/locale/ja/LC_MESSAGES/`` 中的 ``.po`` 文件

3. 检查翻译完成情况（可选）：

   .. code-block:: sh

       python scripts check-po code ja

4. 编译翻译文件（仅在必要时）：

   .. code-block:: sh

       python scripts compile-po code ja

5. 在本地测试翻译效果（运行程序）

6. 提交更改并创建 Pull Request
