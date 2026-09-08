:orphan:

贡献文档国际化
===========================

.. note::

    已有的文档

    - zh_CN: https://janim.readthedocs.io/zh-cn/latest/
    - en: https://janim.readthedocs.io/en/latest/

准备环境
-------------------

假设你已经 fork 仓库并 clone 到了本地。

使用 ``cd JAnim`` 进入项目文件夹，然后安装必要的环境：

.. code-block:: bash

    pip install -e .[gui,doc]

另外，需要确保已安装 `GNU gettext <https://www.gnu.org/software/gettext/>`_

工作流程
-----------

文档国际化的工作流程分为以下步骤：

1. **更新翻译文件**：提取最新的可翻译文本并生成/更新 .po 文件
2. **进行翻译**：编辑 .po 文件进行翻译（必要时可用 ``format-po`` 统一格式）
3. **本地验证**：在本地构建文档预览翻译效果

.. _update-po-files:

更新翻译文件
-------------------

大多数情况下，比如英文文档，翻译文件（后缀 ``.po``）已经生成到了项目中。
如果你只是想编辑已有的翻译文件，可以跳过此段，直接到 :ref:`translate-docs` 便可以开始翻译。

要创建新语言的翻译或更新现有翻译文件，使用以下命令：

.. code-block:: bash

    python scripts update-po docs <language>

其中 ``<language>`` 是你要翻译的语言代码（例如 ``en`` 表示英文，``ja`` 表示日语等）。

.. note::

    ``zh_CN`` 是文档的源语言，因此不需要为其创建翻译文件。

.. 该命令会执行以下步骤：

.. - 提取文档中所有可翻译的文本到 ``.pot`` 文件（在 ``doc/build/gettext/`` 目录中）
.. - 从 ``.pot`` 文件生成或更新相应语言的 ``.po`` 文件（在 ``doc/source/locales/<language>/LC_MESSAGES/`` 目录中）
.. - 自动格式化生成的 ``.po`` 文件

完成后，你可以在相应的 ``doc/source/locales/<language>/LC_MESSAGES/`` 目录中找到所有的 ``.po`` 文件。

检查翻译完成情况
-------------------

在开始翻译或翻译过程中，你可以检查翻译的完成情况：

.. code-block:: bash

    python scripts check-po docs <language>

该命令会扫描所有 ``.po`` 文件，并列出仍有未翻译（untranslated）或模糊（fuzzy）条目的文件。
这有助于你了解还需要进行哪些翻译工作。

并且一些软件，比如 Poedit 的编目管理器也可以列出文件夹中的 ``.po`` 文件的翻译完成情况。

.. _translate-docs:

进行文档翻译
-------------------

现在 ``doc/source/locales/<language>/LC_MESSAGES/`` 中已经存放了翻译文件（后缀 ``.po``）。

可以使用 Poedit 软件来编辑 ``.po`` 文件，或者用任何文本编辑器直接编辑。

.. note::

    如果你有能力检查的话，使用 LLM Agent 翻译也无妨（但是记得校对哦）

如果你是手动编辑了较多 ``.po`` 文件，建议在提交前执行一次：

.. code-block:: bash

    python scripts format-po docs <language>

这个命令会统一 ``.po`` 的换行与排版策略，减少因为格式差异导致的无关 diff。

完成翻译后，提交你的更改，创建合并到 ``main`` 分支的 Pull Request。

在本地构建文档
-------------------

要在本地预览你的翻译效果，可以构建文档：

.. code-block:: bash

    python scripts build-docs <language>

其中 ``<language>`` 是你要构建的语言代码（例如 ``en`` 表示英文）。

该命令会在 ``doc/build/html_i18n/<language>/`` 下生成网页文件，点击其中的 ``index.html`` 即可在浏览器中打开并查看文档。

或者在使用前述命令时加上 ``-o`` 参数，即可直接在构建完成后自动打开浏览器预览：

.. code-block:: bash

    python scripts build-docs <language> -o

.. note::

    构建文档时，会自动从 ``.po`` 文件编译产生 ``.mo`` 文件，无需提前手动生成。

完整操作示例
-------------------

假设你要为文档提供英文翻译，完整流程如下：

1. 更新翻译文件：

   .. code-block:: bash

       python scripts update-po docs en

2. 编辑 ``doc/source/locales/en/LC_MESSAGES/`` 中的 ``.po`` 文件进行翻译

3. 检查翻译完成情况（可选）：

   .. code-block:: bash

       python scripts check-po docs en

4. 在本地构建并打开文档预览：

   .. code-block:: bash

       python scripts build-docs en -o

5. 提交前统一 ``.po`` 文件格式（可选）：

   .. code-block:: bash

       python scripts format-po docs en

6. 提交更改并创建 Pull Request
