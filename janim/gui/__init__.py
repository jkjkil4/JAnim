try:
    # flake8: noqa
    import PySide6
except ImportError:
    print('使用 GUI 界面时需要安装额外模块，但是未安装')
    print('你可以使用 pip install janim[gui] 进行安装，并确保你安装在了正确的 Python 版本中')

    import sys
    sys.exit()
