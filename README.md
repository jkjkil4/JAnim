![logo](logo.png)

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat)](http://choosealicense.com/licenses/mit/)

<div align="center">

**&gt; English &lt;** | [简体中文](README_zh_CN.md)

</div>

## Introduction
JAnim is a library for simple animation effects.

Inspired by [manim](https://github.com/3b1b/manim).

<table>
  <tr>
    <td>
      <img src="./assets/WriteExample.gif"/>
    </td>
    <td>
      <img src="./assets/TextExample.gif"/>
    </td>
    <td>
      <img src="./assets/NumberPlaneExample.gif"/>
    </td>
  </tr>
</table>

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
