![logo](https://raw.githubusercontent.com/jkjkil4/JAnim/main/assets/logo.png)

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat)](http://choosealicense.com/licenses/mit/)
[![PyPI Latest Release](https://img.shields.io/pypi/v/janim.svg?style=flat&logo=pypi)](https://pypi.org/project/JAnim/)
[![zh-CN Documentation Status](https://readthedocs.org/projects/JAnim/badge/?version=latest)](https://janim.readthedocs.io/zh-cn/latest/)

<div align="center">

[English](README.md) | **&gt;简体中文&lt;**

</div>

## 介绍
JAnim 是一个用于创建流畅动画的库，以程序化动画为核心理念，并支持实时编辑、实时预览，并支持更多其它丰富的功能。

受到 [manim](https://github.com/3b1b/manim) 的启发

介绍视频：[https://www.bilibili.com/video/BV17s42137SJ/](https://www.bilibili.com/video/BV17s42137SJ/)

## 示例

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

[- 更多样例 -](https://janim.readthedocs.io/zh-cn/latest/)

</div>

## 亮点

### 程序化动画

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

### 修改代码，立即更新

<div align="center">

![](https://raw.githubusercontent.com/jkjkil4/JAnim/main/assets/CodeRefresh.gif)

</div>

### 随意控制预览进度

<div align="center">

![](https://raw.githubusercontent.com/jkjkil4/JAnim/main/assets/PreviewControl.gif)

</div>

## 安装

JAnim 运行在 Python 3.12 及更高版本

你可以通过以下命令直接安装 JAnim
```sh
pip install janim
```
来安装在 pypi 上发布的最新版本。或者，为了跟上最新的开发进度并编辑源代码，你可以通过以下命令克隆此仓库
```sh
git clone https://github.com/jkjkil4/JAnim.git
cd JAnim
pip install -e .
```

另外，还需要安装其他软件依赖:
- 要生成视频文件，请安装 [FFmpeg](https://ffmpeg.org/).
- 要使用 Typst，请安装 [Typst](https://github.com/typst/typst).

## 使用 JAnim

你可以使用如下的命令来查看示例
```sh
janim examples
```

[文档](https://janim.readthedocs.io/zh-cn/latest/index.html)提供了更为详细的 JAnim 安装与使用教程（注：你可以使用页面角落的弹出菜单来更改文档语言）

## License

MIT license
