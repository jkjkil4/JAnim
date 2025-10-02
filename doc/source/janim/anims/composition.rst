composition
===========

.. raw:: html

    <script>
        const animTimeUnit = 100;

        function updateAnimation(input_suffix, names) {
            const lagRatio = parseFloat(document.getElementById('lag_ratio' + input_suffix).value);
            const offset = parseFloat(document.getElementById('offset' + input_suffix).value);

            document.getElementById('lag_ratio_value' + input_suffix).innerText = lagRatio;
            document.getElementById('offset_value' + input_suffix).innerText = offset;

            const anims = names.map(name => document.getElementById(name));

            const offsets = [0, 0, 0, 0];

            let start = 0;
            let globalOffset = 0;

            for (const anim of anims) {
                const width = anim.clientWidth;
                anim.leftSpacing = start;
                if (anim.leftSpacing < 0)
                    globalOffset = Math.max(globalOffset, -anim.leftSpacing);
                start += lagRatio * width + offset * animTimeUnit;
            }

            for (const anim of anims) {
                anim.style.left = `${anim.leftSpacing + globalOffset}px`;
            }
        }
    </script>

.. autoclass:: janim.anims.composition.AnimGroup
    :show-inheritance:

``lag_ratio`` 与 ``offset`` 的交互式示例：

.. raw:: html

    <div class="anim-timing-example">
        <div class="anim-timing-interactive">
            <div class="anim-arg-input">
                <label for="lag_ratio">lag_ratio: </label>
                <span id="lag_ratio_value_AG">0</span>
                <input type="range" id="lag_ratio_AG" min="0" max="1" step="0.01" value="0" oninput="updateAnimation_AnimGroup()">
            </div>
            <div class="anim-arg-input">
                <label for="offset">offset (s): </label>
                <span id="offset_value_AG">0</span>
                <input type="range" id="offset_AG" min="-1" max="2.5" step="0.05" value="0" oninput="updateAnimation_AnimGroup()">
            </div>

            <div class="anim-boxes">
                <div id="anim1_AG" class="animation-box" style="top: 5px; left: 0px;">
                    <span>Anim1 1s</span>
                </div>
                <div id="anim2_AG" class="animation-box" style="top: 10px; left: 0px;">
                    <span>Anim2 1s</span>
                </div>
                <div id="anim3_AG" class="animation-box" style="top: 15px; left: 0px; width: 200px;">
                    <span>Anim3 2s</span>
                </div>
                <div id="anim4_AG" class="animation-box" style="top: 20px; left: 0px;">
                    <span>Anim4 1s</span>
                </div>
            </div>
        </div>
    </div>
    <script>
        const names_AnimGroup = ['anim1_AG', 'anim2_AG', 'anim3_AG', 'anim4_AG'];

        function updateAnimation_AnimGroup() {
            updateAnimation('_AG', names_AnimGroup);
        }
        updateAnimation_AnimGroup();
    </script>

.. janim-example:: AnimGroupExample
    :media: ../../_static/videos/AnimGroupExample.mp4

    from janim.imports import *

    class AnimGroupExample(Timeline):
        def construct(self):
            group = Group(
                Circle(fill_alpha=0.5),
                Square(fill_alpha=0.5),
                Text('Text', font_size=48),
                color=BLUE
            )
            group.points.arrange(buff=LARGE_BUFF)

            self.forward()
            self.play(
                FadeIn(group[0]),
                AnimGroup(
                    FadeIn(group[1]),
                    FadeIn(group[2]),
                    duration=2
                )
            )
            self.forward()

            self.hide(group)
            self.play(
                FadeIn(group[0], duration=2),
                AnimGroup(
                    FadeIn(group[1]),
                    FadeIn(group[2]),
                    at=1,
                    duration=2
                )
            )
            self.forward()

.. note::

    为了更好地了解这些动画组合的效果，你可以复制到你的文件中运行，这样你就可以在界面上看到子动画对应的区段

.. autoclass:: janim.anims.composition.Succession
    :show-inheritance:

``lag_ratio`` 与 ``offset`` 的交互式示例：

.. raw:: html

    <div class='anim-timing-example'>
        <div class='anim-timing-interactive'>
            <div class="anim-arg-input">
                <label for="lag_ratio">lag_ratio: </label>
                <span id="lag_ratio_value_S">0</span>
                <input type="range" id="lag_ratio_S" min="0" max="1" step="0.01" value="1" oninput="updateAnimation_Succession()">
            </div>
            <div class="anim-arg-input">
                <label for="offset">offset (s): </label>
                <span id="offset_value_S">0</span>
                <input type="range" id="offset_S" min="-1" max="2.5" step="0.05" value="0" oninput="updateAnimation_Succession()">
            </div>

            <div class="anim-boxes">
                <div id="anim1_S" class="animation-box" style="top: 5px; left: 0px;">
                    <span>Anim1 1s</span>
                </div>
                <div id="anim2_S" class="animation-box" style="top: 10px; left: 0px;">
                    <span>Anim2 1s</span>
                </div>
                <div id="anim3_S" class="animation-box" style="top: 15px; left: 0px; width: 200px;">
                    <span>Anim3 2s</span>
                </div>
                <div id="anim4_S" class="animation-box" style="top: 20px; left: 0px;">
                    <span>Anim4 1s</span>
                </div>
            </div>
        </div>
    </div>
    <script>
        const names_Succession = ['anim1_S', 'anim2_S', 'anim3_S', 'anim4_S'];

        function updateAnimation_Succession() {
            updateAnimation('_S', names_Succession);
        }
        updateAnimation_Succession();
    </script>

.. janim-example:: SuccessionExample
    :media: ../../_static/videos/SuccessionExample.mp4

    from janim.imports import *

    class SuccessionExample(Timeline):
        def construct(self):
            group = Group(
                Circle(fill_alpha=0.5),
                Square(fill_alpha=0.5),
                Text('Text', font_size=48),
                color=BLUE
            )
            group.points.arrange(buff=LARGE_BUFF)

            self.forward()
            self.play(
                Succession(
                    *map(FadeIn, group)
                )
            )
            self.forward()

            self.hide(group)
            self.play(
                Succession(
                    *map(FadeIn, group),
                    offset=1
                )
            )
            self.forward()

            self.hide(group)
            self.play(
                Succession(
                    *map(FadeIn, group),
                    offset=-0.7
                )
            )
            self.forward()

.. autoclass:: janim.anims.composition.Aligned
    :show-inheritance:

.. warning::

    视频示例的代码在下方，不是上方的时间示例

.. janim-example:: AlignedExample
    :media: ../../_static/videos/AlignedExample.mp4

    from janim.imports import *

    class AlignedExample(Timeline):
        def construct(self):
            group = Group(
                Circle(fill_alpha=0.5),
                Square(fill_alpha=0.5),
                Text('Text', font_size=48),
                color=BLUE
            )
            group.points.arrange(buff=LARGE_BUFF)

            self.forward()
            self.play(
                Aligned(
                    FadeIn(group[0], duration=2),
                    FadeIn(group[1], duration=3),
                    FadeIn(group[2], at=0.5, duration=0.5)
                )
            )
            self.forward()

.. autoclass:: janim.anims.composition.Wait
    :show-inheritance:

.. autoclass:: janim.anims.composition.Do
    :show-inheritance:
