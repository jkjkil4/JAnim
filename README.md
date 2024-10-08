![logo](logo.png)

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat)](http://choosealicense.com/licenses/mit/)

<div align="center">

**&gt; English &lt;** | [简体中文](README_zh_CN.md)

</div>

## Introduction
JAnim is a library for creating smooth animations.

Inspired by [manim](https://github.com/3b1b/manim).

Promotional video: [https://www.bilibili.com/video/BV17s42137SJ/](https://www.bilibili.com/video/BV17s42137SJ/)

<table>
  <tr>
    <td>
      <img src="./assets/TextExample.gif"/>
    </td>
    <td>
      <img src="./assets/RiemmanIntegral.gif"/>
    </td>
    <td>
      <img src="./assets/NumberPlaneExample.gif"/>
    </td>
  </tr>
</table>

<!-- ffmpeg -i xxx.mp4 -filter:v "setpts=0.5*PTS" -r 15 -s 720x405 xxx.gif -->

___

Video：[https://www.bilibili.com/video/BV1hCYQe3EpG/?t=179](https://www.bilibili.com/video/BV1hCYQe3EpG/?t=179)

Source code：[https://github.com/jkjkil4/videos/blob/main/2024/VideoEncoding/code.py](https://github.com/jkjkil4/videos/blob/main/2024/VideoEncoding/code.py)

<div align="center">

![](./assets/RealSolution.gif)

</div>

___

Video：[https://www.bilibili.com/video/BV1CkxuexEeQ/?p=3&t=118](https://www.bilibili.com/video/BV1CkxuexEeQ/?p=3&t=118)

Source code：[https://github.com/jkjkil4/videos/blob/main/2024/LearnOpenGL-8-MoreAttr/code.py](https://github.com/jkjkil4/videos/blob/main/2024/LearnOpenGL-8-MoreAttr/code.py)

<div align="center">

![](./assets/FragInterp.gif)

</div>

## Installation

> ⚠️ JAnim does not work on macOS.

JAnim runs on Python 3.12+ and OpenGL 4.3+.

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
- To generate video files, install [ffmpeg](https://ffmpeg.org/).
- To use `Typst`, install [typst](https://github.com/typst/typst).


## Using JAnim

You can run the following command to see examples.
```sh
janim examples
```

The [Tutorial Page](https://janim.readthedocs.io/en/latest/tutorial/installation.html) of the [Documentation](https://janim.readthedocs.io/en/latest/index.html) provides a brief view to get you started. (Note: You can change the language of the documentation at the bottom-left corner.)

## License

MIT license
