constants
=========

间距
-----------

.. code-block:: python

    SMALL_BUFF = 0.1
    MED_SMALL_BUFF = 0.25
    MED_LARGE_BUFF = 0.5
    LARGE_BUFF = 1

    DEFAULT_ITEM_TO_EDGE_BUFF = MED_LARGE_BUFF  # Distance between object and edge
    DEFAULT_ITEM_TO_ITEM_BUFF = MED_SMALL_BUFF  # Distance between objects

坐标
-----------

JAnim 使用三维坐标，并且用 ``ndarray`` 的类型

.. code-block:: python

    ORIGIN = np.array((0., 0., 0.))
    UP = np.array((0., 1., 0.))
    DOWN = np.array((0., -1., 0.))
    RIGHT = np.array((1., 0., 0.))
    LEFT = np.array((-1., 0., 0.))
    IN = np.array((0., 0., -1.))
    OUT = np.array((0., 0., 1.))
    X_AXIS = np.array((1., 0., 0.))
    Y_AXIS = np.array((0., 1., 0.))
    Z_AXIS = np.array((0., 0., 1.))

    NAN_POINT = np.full(3, np.nan)

    # Useful abbreviations for diagonals
    UL = UP + LEFT
    UR = UP + RIGHT
    DL = DOWN + LEFT
    DR = DOWN + RIGHT

.. tip::

    可以通过 ``Config.get`` 得到画面边界上的坐标

    .. code-block:: python

        Config.get.left_side
        Config.get.right_side
        Config.get.bottom
        Config.get.top

    另见：:class:`~.Config`

数学常数
---------------------

.. code-block:: python

    PI = np.pi
    TAU = 2 * PI
    DEGREES = TAU / 360
    # Nice to have a constant for readability
    # when juxtaposed with expressions like 30 * DEGREES
    RADIANS = 1

颜色
---------------------

颜色相关工具和预览可以使用：

- JAnim 自带工具：在命令行中输入 ``janim tool color`` 或者在 GUI 界面左上角的“功能”中点击“颜色”
- 在线工具：`颜色工具 - MK官网 <https://manim.org.cn/tool/color>`_

这里是 JAnim 中定义的颜色的预览：(修改自
`docs.manim.org.cn <https://docs.manim.org.cn/documentation/constants.html>`_ (备份页面 `manimgl-zh.readthedocs.io <https://manimgl-zh.readthedocs.io/zh-cn/latest/documentation/constants.html>`_))

.. raw:: html

    <div style="float: left;">
        <h3>BLUE</h3>
        <div class="colors BLUE_E"><p class="color-text">BLUE_E</p></div>
        <div class="colors BLUE_D"><p class="color-text">BLUE_D</p></div>
        <div class="colors BLUE_C"><p class="color-text">BLUE_C</p></div>
        <div class="colors BLUE_B"><p class="color-text">BLUE_B</p></div>
        <div class="colors BLUE_A"><p class="color-text">BLUE_A</p></div>
    </div>
    <div style="float: left;">
        <h3>TEAL</h3>
        <div class="colors TEAL_E"><p class="color-text">TEAL_E</p></div>
        <div class="colors TEAL_D"><p class="color-text">TEAL_D</p></div>
        <div class="colors TEAL_C"><p class="color-text">TEAL_C</p></div>
        <div class="colors TEAL_B"><p class="color-text">TEAL_B</p></div>
        <div class="colors TEAL_A"><p class="color-text">TEAL_A</p></div>
    </div>
    <div style="float: left;">
        <h3>GREEN</h3>
        <div class="colors GREEN_E"><p class="color-text">GREEN_E</p></div>
        <div class="colors GREEN_D"><p class="color-text">GREEN_D</p></div>
        <div class="colors GREEN_C"><p class="color-text">GREEN_C</p></div>
        <div class="colors GREEN_B"><p class="color-text">GREEN_B</p></div>
        <div class="colors GREEN_A"><p class="color-text">GREEN_A</p></div>
    </div>
    <div style="float: left;">
        <h3>YELLOW</h3>
        <div class="colors YELLOW_E"><p class="color-text">YELLOW_E</p></div>
        <div class="colors YELLOW_D"><p class="color-text">YELLOW_D</p></div>
        <div class="colors YELLOW_C"><p class="color-text">YELLOW_C</p></div>
        <div class="colors YELLOW_B"><p class="color-text">YELLOW_B</p></div>
        <div class="colors YELLOW_A"><p class="color-text">YELLOW_A</p></div>
    </div>
    <div style="float: left;">
        <h3>GOLD</h3>
        <div class="colors GOLD_E"><p class="color-text">GOLD_E</p></div>
        <div class="colors GOLD_D"><p class="color-text">GOLD_D</p></div>
        <div class="colors GOLD_C"><p class="color-text">GOLD_C</p></div>
        <div class="colors GOLD_B"><p class="color-text">GOLD_B</p></div>
        <div class="colors GOLD_A"><p class="color-text">GOLD_A</p></div>
    </div>
    <div style="float: left;">
        <h3>RED</h3>
        <div class="colors RED_E"><p class="color-text">RED_E</p></div>
        <div class="colors RED_D"><p class="color-text">RED_D</p></div>
        <div class="colors RED_C"><p class="color-text">RED_C</p></div>
        <div class="colors RED_B"><p class="color-text">RED_B</p></div>
        <div class="colors RED_A"><p class="color-text">RED_A</p></div>
    </div>
    <div style="float: left;">
        <h3>MAROON</h3>
        <div class="colors MAROON_E"><p class="color-text">MAROON_E</p></div>
        <div class="colors MAROON_D"><p class="color-text">MAROON_D</p></div>
        <div class="colors MAROON_C"><p class="color-text">MAROON_C</p></div>
        <div class="colors MAROON_B"><p class="color-text">MAROON_B</p></div>
        <div class="colors MAROON_A"><p class="color-text">MAROON_A</p></div>
    </div>
    <div style="float: left;">
        <h3>PURPLE</h3>
        <div class="colors PURPLE_E"><p class="color-text">PURPLE_E</p></div>
        <div class="colors PURPLE_D"><p class="color-text">PURPLE_D</p></div>
        <div class="colors PURPLE_C"><p class="color-text">PURPLE_C</p></div>
        <div class="colors PURPLE_B"><p class="color-text">PURPLE_B</p></div>
        <div class="colors PURPLE_A"><p class="color-text">PURPLE_A</p></div>
    </div>
    <div style="float: left;">
        <h3>GREY</h3>
        <div class="colors GREY_E"><p class="color-text">GREY_E</p></div>
        <div class="colors GREY_D"><p class="color-text">GREY_D</p></div>
        <div class="colors GREY_C"><p class="color-text">GREY_C</p></div>
        <div class="colors GREY_B"><p class="color-text">GREY_B</p></div>
        <div class="colors GREY_A"><p class="color-text">GREY_A</p></div>
    </div>
    <div style="float: left;">
        <h3>Others</h3>
        <div class="colors WHITE"><p class="color-text" style="color: BLACK">WHITE</p></div>
        <div class="colors BLACK"><p class="color-text">BLACK</p></div>
        <div class="colors GREY_BROWN"><p class="color-text-small">GREY_BROWN</p></div>
        <div class="colors DARK_BROWN"><p class="color-text-small">DARK_BROWN</p></div>
        <div class="colors LIGHT_BROWN"><p class="color-text-small">LIGHT_BROWN</p></div>
        <div class="colors PINK"><p class="color-text">PINK</p></div>
        <div class="colors LIGHT_PINK"><p class="color-text-small">LIGHT_PINK</p></div>
        <div class="colors GREEN_SCREEN"><p class="color-text-small">GREEN_SCREEN</p></div>
        <div class="colors ORANGE"><p class="color-text">ORANGE</p></div>
    </div>
