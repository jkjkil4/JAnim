![logo](https://raw.githubusercontent.com/jkjkil4/JAnim/main/assets/logo.png)

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat)](http://choosealicense.com/licenses/mit/)
[![PyPI Latest Release](https://img.shields.io/pypi/v/janim.svg?style=flat&logo=pypi)](https://pypi.org/project/JAnim/)
[![en Documentation Status](https://readthedocs.org/projects/JAnim-en/badge/?version=latest)](https://janim.readthedocs.io/en/latest/)

<div align="center">

**&gt; English &lt;** | [简体中文](README_zh_CN.md)

</div>

## Introduction
JAnim is a library for creating smooth animations, built around the core concept of programmatic animation. It supports real-time editing, live preview, and a wide range of additional powerful features.

Inspired by [manim](https://github.com/3b1b/manim).

Introduction video: [https://www.bilibili.com/video/BV17s42137SJ/](https://www.bilibili.com/video/BV17s42137SJ/)

## Examples

<table>
  <tr>
    <td>
      <img src="https://raw.githubusercontent.com/jkjkil4/JAnim/main/assets/RealSolution.gif"/>
    </td>
    <td>
      <img src="https://raw.githubusercontent.com/jkjkil4/JAnim/main/assets/NumberPlaneExample.gif"/>
    </td>
    <td>
      <img src="https://raw.githubusercontent.com/jkjkil4/JAnim/main/assets/FragInterp.gif"/>
    </td>
  </tr>
</table>

<!-- ffmpeg -i xxx.mp4 -filter:v "setpts=0.5*PTS" -r 15 -s 720x405 xxx.gif -->

<div align="center">

[- More Examples -](https://janim.readthedocs.io/en/latest/)

</div>

## Highlights

### Programmatic animation

```py
class BubbleSort(Timeline):
    def construct(self):
        # define items
        heights = np.linspace(1.0, 6.0, 5)
        np.random.seed(123456)
        np.random.shuffle(heights)
        rects = [
            Rect(1, height,
                 fill_alpha=0.5)
            for height in heights
        ]

        group = Group(*rects)
        group.points.arrange(aligned_edge=DOWN)

        # do animations
        self.show(group)

        for i in range(len(heights) - 1, 0, -1):
            for j in range(i):
                rect1, rect2 = rects[j], rects[j + 1]

                self.play(
                    rect1.anim.color.set(BLUE),
                    rect2.anim.color.set(BLUE),
                    duration=0.15
                )

                if heights[j] > heights[j + 1]:
                    x1 = rect1.points.box.x
                    x2 = rect2.points.box.x

                    self.play(
                        rect1.anim.points.set_x(x2),
                        rect2.anim.points.set_x(x1),
                        duration=0.3
                    )

                    heights[[j, j + 1]] = heights[[j + 1, j]]
                    rects[j], rects[j + 1] = rect2, rect1

                self.play(
                    rect1.anim.color.set(WHITE),
                    rect2.anim.color.set(WHITE),
                    duration=0.15
                )
```

<div align="center">

![](https://raw.githubusercontent.com/jkjkil4/JAnim/main/assets/BubbleSort.gif)

</div>

### Change the code, refresh right away

<div align="center">

![](https://raw.githubusercontent.com/jkjkil4/JAnim/main/assets/CodeRefresh.gif)

</div>

### Freely control the preview progress

<div align="center">

![](https://raw.githubusercontent.com/jkjkil4/JAnim/main/assets/PreviewControl.gif)

</div>

## Installation

JAnim runs on Python 3.12+

You may install JAnim directly via
```sh
pip install janim
```
to install the latest version distributed on pypi. Or, to catch up with the latest development and edit the source code, you may clone this repository via
```sh
git clone https://github.com/jkjkil4/JAnim.git
cd JAnim
pip install -e .
```

Additionally, there are other software dependencies to be installed:
- To generate video files, install [FFmpeg](https://ffmpeg.org/).
- To use Typst, install [Typst](https://github.com/typst/typst).

## Using JAnim

You can run the following command to see examples.
```sh
janim examples
```

The [Documentation](https://janim.readthedocs.io/zh-cn/latest/index.html) provides a more detailed guide on installing and using JAnim. (Note: You can change the documentation language using the flyout menu at the corner of the page.)

## License

MIT license
