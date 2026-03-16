基准测试
=======================

准备环境
-------------------

假设你已经 fork 仓库并 clone 到了本地。

使用 ``cd JAnim`` 进入项目文件夹，然后安装包含基准测试所需依赖的环境：

.. code-block:: bash

    pip install -e .[bench]

运行基准测试
-------------------

项目提供了一个方便的脚本入口来运行基准测试。命令格式为：

.. code-block:: bash

   python scripts bench [options]

可用选项示例：

- ``--untested_tags``：测试自 v2.1.0 之后所有尚未测试的 tag。
- ``--tags <tag> [<tag> ...]``：按一或多个标签运行测试，例如 ``--tags v2.1.0 v2.2.0``。
- ``--hashes <hash> [<hash> ...]``：按提交哈希运行测试（可传入多个）。
- ``-o`` / ``--open``：自动在浏览器中打开预览。

运行示例
--------------

1. 测试所有未测试的 tag（在 v2.1.0 之后）：

.. code-block:: bash

   python scripts bench --untested_tags

2. 测试指定标签：

.. code-block:: bash

   python scripts bench --tags v2.1.0 v2.2.0

3. 使用指定哈希测试并自动打开预览：

.. code-block:: bash

   python scripts bench --hashes 78b7c20 2c1fcfd -o

- 你也可以直接使用 ``asv preview -b`` 在本地预览已经发布的结果。

脚本行为说明
----------------

- 当使用 ``--untested_tags`` 时，脚本会查询仓库中自 v2.1.0 之后的 tag 的对应哈希（项目内部实现位于 ``scripts/bench/hashes.py``），并与已测试的哈希进行比对，只对尚未测试的提交运行基准。
- 如果同时传入 ``--tags`` 或 ``--hashes``，也会将它们加入待测哈希列表。
- 在开始运行前，脚本会把要测试的哈希列表写入 ``.asv/_tag_hashes.txt``，并调用 ``asv run HASHFILE:.asv/_tag_hashes.txt`` 运行基准用例，随后使用 ``asv publish`` 将结果发布到本地，最后（可选）调用 ``asv preview -b`` 打开浏览器预览。
