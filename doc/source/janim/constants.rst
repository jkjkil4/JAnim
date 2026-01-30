constants
=========

间距
-----------

.. code-block:: python

    SMALL_BUFF = 0.1
    MED_SMALL_BUFF = 0.25
    MED_LARGE_BUFF = 0.5
    LARGE_BUFF = 1

    DEFAULT_ITEM_TO_EDGE_BUFF = MED_LARGE_BUFF  # Distance between item and edge
    DEFAULT_ITEM_TO_ITEM_BUFF = MED_SMALL_BUFF  # Distance between items

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

.. _constants_colors:

颜色
---------------------

颜色相关工具和预览可以使用：

- JAnim 自带工具：在命令行中输入 ``janim tool color`` 或者在 GUI 界面左上角的“工具”中点击“颜色”
- 在线工具：`颜色工具 - MK官网 <https://manim.org.cn/tool/color>`_

这里是 JAnim 中定义的颜色的预览：(修改自
`docs.manim.org.cn <https://docs.manim.org.cn/documentation/constants.html>`_ (备份页面 `manimgl-zh.readthedocs.io <https://manimgl-zh.readthedocs.io/zh-cn/latest/documentation/constants.html>`_))

.. raw:: html

    <h3>BLUE</h3>
    <div class="color-group">
        <div class="colors BLUE_E"><p class="color-text">BLUE_E</p><p class="color-hex">#1C758A</p></div>
        <div class="colors BLUE_D"><p class="color-text">BLUE_D</p><p class="color-hex">#29ABCA</p></div>
        <div class="colors BLUE_C"><p class="color-text">BLUE_C</p><p class="color-hex">#58C4DD</p></div>
        <div class="colors BLUE_B"><p class="color-text">BLUE_B</p><p class="color-hex">#9CDCEB</p></div>
        <div class="colors BLUE_A"><p class="color-text">BLUE_A</p><p class="color-hex">#C7E9F1</p></div>
    </div>
    <h3>TEAL</h3>
    <div class="color-group">
        <div class="colors TEAL_E"><p class="color-text">TEAL_E</p><p class="color-hex">#49A88F</p></div>
        <div class="colors TEAL_D"><p class="color-text">TEAL_D</p><p class="color-hex">#55C1A7</p></div>
        <div class="colors TEAL_C"><p class="color-text">TEAL_C</p><p class="color-hex">#5CD0B3</p></div>
        <div class="colors TEAL_B"><p class="color-text">TEAL_B</p><p class="color-hex">#76DDC0</p></div>
        <div class="colors TEAL_A"><p class="color-text">TEAL_A</p><p class="color-hex">#ACEAD7</p></div>
    </div>
    <h3>GREEN</h3>
    <div class="color-group">
        <div class="colors GREEN_E"><p class="color-text">GREEN_E</p><p class="color-hex">#699C52</p></div>
        <div class="colors GREEN_D"><p class="color-text">GREEN_D</p><p class="color-hex">#77B05D</p></div>
        <div class="colors GREEN_C"><p class="color-text">GREEN_C</p><p class="color-hex">#83C167</p></div>
        <div class="colors GREEN_B"><p class="color-text">GREEN_B</p><p class="color-hex">#A6CF8C</p></div>
        <div class="colors GREEN_A"><p class="color-text">GREEN_A</p><p class="color-hex">#C9E2AE</p></div>
    </div>
    <h3>YELLOW</h3>
    <div class="color-group">
        <div class="colors YELLOW_E"><p class="color-text">YELLOW_E</p><p class="color-hex">#E8C11C</p></div>
        <div class="colors YELLOW_D"><p class="color-text">YELLOW_D</p><p class="color-hex">#F4D345</p></div>
        <div class="colors YELLOW_C"><p class="color-text">YELLOW_C</p><p class="color-hex">#FFFF00</p></div>
        <div class="colors YELLOW_B"><p class="color-text">YELLOW_B</p><p class="color-hex">#FFEA94</p></div>
        <div class="colors YELLOW_A"><p class="color-text">YELLOW_A</p><p class="color-hex">#FFF1B6</p></div>
    </div>
    <h3>GOLD</h3>
    <div class="color-group">
        <div class="colors GOLD_E"><p class="color-text">GOLD_E</p><p class="color-hex">#C78D46</p></div>
        <div class="colors GOLD_D"><p class="color-text">GOLD_D</p><p class="color-hex">#E1A158</p></div>
        <div class="colors GOLD_C"><p class="color-text">GOLD_C</p><p class="color-hex">#F0AC5F</p></div>
        <div class="colors GOLD_B"><p class="color-text">GOLD_B</p><p class="color-hex">#F9B775</p></div>
        <div class="colors GOLD_A"><p class="color-text">GOLD_A</p><p class="color-hex">#F7C797</p></div>
    </div>
    <h3>RED</h3>
    <div class="color-group">
        <div class="colors RED_E"><p class="color-text">RED_E</p><p class="color-hex">#CF5044</p></div>
        <div class="colors RED_D"><p class="color-text">RED_D</p><p class="color-hex">#E65A4C</p></div>
        <div class="colors RED_C"><p class="color-text">RED_C</p><p class="color-hex">#FC6255</p></div>
        <div class="colors RED_B"><p class="color-text">RED_B</p><p class="color-hex">#FF8080</p></div>
        <div class="colors RED_A"><p class="color-text">RED_A</p><p class="color-hex">#F7A1A3</p></div>
    </div>
    <h3>MAROON</h3>
    <div class="color-group">
        <div class="colors MAROON_E"><p class="color-text">MAROON_E</p><p class="color-hex">#94424F</p></div>
        <div class="colors MAROON_D"><p class="color-text">MAROON_D</p><p class="color-hex">#A24D61</p></div>
        <div class="colors MAROON_C"><p class="color-text">MAROON_C</p><p class="color-hex">#C55F73</p></div>
        <div class="colors MAROON_B"><p class="color-text">MAROON_B</p><p class="color-hex">#EC92AB</p></div>
        <div class="colors MAROON_A"><p class="color-text">MAROON_A</p><p class="color-hex">#ECABC1</p></div>
    </div>
    <h3>PURPLE</h3>
    <div class="color-group">
        <div class="colors PURPLE_E"><p class="color-text">PURPLE_E</p><p class="color-hex">#644172</p></div>
        <div class="colors PURPLE_D"><p class="color-text">PURPLE_D</p><p class="color-hex">#715582</p></div>
        <div class="colors PURPLE_C"><p class="color-text">PURPLE_C</p><p class="color-hex">#9A72AC</p></div>
        <div class="colors PURPLE_B"><p class="color-text">PURPLE_B</p><p class="color-hex">#B189C6</p></div>
        <div class="colors PURPLE_A"><p class="color-text">PURPLE_A</p><p class="color-hex">#CAA3E8</p></div>
    </div>
    <h3>GREY</h3>
    <div class="color-group">
        <div class="colors GREY_E"><p class="color-text">GREY_E</p><p class="color-hex">#222222</p></div>
        <div class="colors GREY_D"><p class="color-text">GREY_D</p><p class="color-hex">#444444</p></div>
        <div class="colors GREY_C"><p class="color-text">GREY_C</p><p class="color-hex">#888888</p></div>
        <div class="colors GREY_B"><p class="color-text">GREY_B</p><p class="color-hex">#BBBBBB</p></div>
        <div class="colors GREY_A"><p class="color-text">GREY_A</p><p class="color-hex">#DDDDDD</p></div>
    </div>
    <h3>Others</h3>
    <div class="color-group">
        <div>
            <div class="colors PURE_RED"><p class="color-text-s">PURE_RED</p><p class="color-hex-s">#FF0000</p></div>
            <div class="colors PURE_GREEN"><p class="color-text-s">PURE_GREEN</p><p class="color-hex-s">#00FF00</p></div>
            <div class="colors PURE_BLUE"><p class="color-text-s">PURE_BLUE</p><p class="color-hex-s">#0000FF</p></div>
        </div>
        <div>
            <div class="colors WHITE"><p class="color-text" style="color: BLACK">WHITE</p><p class="color-hex" style="color: BLACK">#FFFFFF</p></div>
            <div class="colors BLACK"><p class="color-text">BLACK</p><p class="color-hex">#000000</p></div>
            <div class="colors GREY_BROWN"><p class="color-text-s">GREY_BROWN</p><p class="color-hex-s">#736357</p></div>
            <div class="colors DARK_BROWN"><p class="color-text-s">DARK_BROWN</p><p class="color-hex-s">#8B4513</p></div>
            <div class="colors LIGHT_BROWN"><p class="color-text-s">LIGHT_BROWN</p><p class="color-hex-s">#CD853F</p></div>
            <div class="colors ORANGE"><p class="color-text">ORANGE</p><p class="color-hex">#FF862F</p></div>
        </div>
        <div>
            <div class="colors PINK"><p class="color-text">PINK</p><p class="color-hex">#D147BD</p></div>
            <div class="colors LIGHT_PINK"><p class="color-text-s">LIGHT_PINK</p><p class="color-hex-s">#DC75CD</p></div>
        </div>
    </div>

.. note::

    由于历史遗留因素，这里的 ``YELLOW_C`` 与 ``YELLOW_`` 系的颜色并不一致
