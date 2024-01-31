import importlib.util
import os


def get_janim_dir() -> str:
    '''
    得到 janim 的路径
    '''
    return os.path.dirname(importlib.util.find_spec('janim').origin)


def readall(filepath: str) -> str:
    '''
    从文件中读取所有字符
    '''
    with open(filepath, 'rt') as f:
        return f.read()
