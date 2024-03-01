import importlib.util
import os

from janim.utils.config import Config


def guarantee_existence(path: str) -> str:
    if not os.path.exists(path):
        os.makedirs(path)
    return os.path.abspath(path)


def get_janim_dir() -> str:
    '''
    得到 janim 的路径
    '''
    return os.path.dirname(importlib.util.find_spec('janim').origin)


def get_typst_temp_dir() -> str:
    return guarantee_existence(os.path.join(Config.get.temp_dir, 'Typst'))


def readall(filepath: str) -> str:
    '''
    从文件中读取所有字符
    '''
    with open(filepath, 'rt') as f:
        return f.read()
