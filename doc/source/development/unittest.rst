单元测试与覆盖率
=======================

准备环境
-------------------

假设你已经 fork 仓库并 clone 到了本地。

使用 ``cd JAnim`` 进入项目文件夹，然后安装包含测试依赖的环境：

.. code-block:: bash

    pip install -e .[test]

运行测试
---------

使用以下命令运行所有测试：

.. code-block:: bash

   python scripts test-cov

这个命令会使用 ``coverage`` 执行测试套件，并对代码覆盖率进行分析，分析结果会被保存为项目根目录下的 ``.coverage`` 文件。

生成覆盖率报告
--------------

你可以使用 ``--html`` 选项生成一个详细的 HTML 覆盖率报告，并自动在默认浏览器中打开：

.. code-block:: bash

   python scripts test-cov --html

.. note::

    目前 JAnim 的代码覆盖率还很低。如果你有兴趣提高代码的测试覆盖率，欢迎贡献更多的测试用例
