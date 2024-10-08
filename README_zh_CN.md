![logo](logo.png)

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat)](http://choosealicense.com/licenses/mit/)

<div align="center">

[English](README.md) | **&gt;简体中文&lt;**

</div>

## 介绍
JAnim 是一个用于创建流畅动画的库

受到 [manim](https://github.com/3b1b/manim) 的启发

宣传视频：[https://www.bilibili.com/video/BV17s42137SJ/](https://www.bilibili.com/video/BV17s42137SJ/)

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

<!-- ffmpeg -i xxx.mp4 -filter:v "setpts=0.5*PTS" -r 15 -s 480x270 xxx.gif -->

<table style="table-layout: fixed; width: 100%;">
  <tr>
    <td rowspan="2" style="width: 40%">
      <img src="./assets/RealSolution.gif">
    </td>
    <td style="width: 60%">
      视频：<a href="https://www.bilibili.com/video/BV1hCYQe3EpG/?t=179">https://www.bilibili.com/video/BV1hCYQe3EpG/?t=179</a>
    </td>
  </tr>
  <tr>
    <td style="width: 60%">
      源代码：<a href="https://github.com/jkjkil4/videos/blob/main/2024/VideoEncoding/code.py">https://github.com/jkjkil4/videos/blob/main/2024/VideoEncoding/code.py</a>
    </td>
  </tr>

  <tr>
    <td rowspan="2" style="width: 40%">
      <img src="./assets/FragInterp.gif">
    </td>
    <td style="width: 60%">
      视频：<a href="https://www.bilibili.com/video/BV1CkxuexEeQ/?p=3&t=118">https://www.bilibili.com/video/BV1CkxuexEeQ/?p=3&t=118</a>
    </td>
  </tr>
  <tr>
    <td style="width: 60%">
      源代码：<a href="https://github.com/jkjkil4/videos/blob/main/2024/LearnOpenGL-8-MoreAttr/code.py">https://github.com/jkjkil4/videos/blob/main/2024/LearnOpenGL-8-MoreAttr/code.py</a>
    </td>
  </tr>
</table>

## 安装

> ⚠️ macOS 无法使用 JAnim

JAnim 运行在 Python 3.12 及更高版本，并且需要 OpenGL 4.3 及更高版本

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
- 要生成视频文件，请安装 [ffmpeg](https://ffmpeg.org/).
- 要使用 Typst，请安装 [typst](https://github.com/typst/typst).


## 使用 JAnim

你可以使用如下的命令来查看示例
```sh
janim examples
```

[文档](https://janim.readthedocs.io/zh-cn/latest/index.html)的[教程页面](https://janim.readthedocs.io/zh-cn/latest/tutorial/installation.html)提供了一个简要的入门指南（注：你可以在文档的左下角更改语言）

## License

MIT license
