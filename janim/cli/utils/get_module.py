import importlib
import linecache
import os
import sys
import types

from janim.exception import EXITCODE_MODULE_NOT_FOUND, EXITCODE_NOT_FILE, ExitException
from janim.locale import get_translator
from janim.logger import log
from janim.utils.file_ops import STDIN_FILENAME

_ = get_translator('janim.cli.utils.get_module')


def get_module(file: str):
    """
    根据给定的输入 ``file`` 产生 ``module``

    - 当 ``file`` 为文件路径时，将文件读取为 module
    - 当 ``file`` 为 ``'-'`` 时，从 ``stdin`` 读取源码编译 module
    """
    if file == '-':
        return get_module_from_stdin()
    else:
        return get_module_from_file(file)


def get_module_from_stdin():
    """
    从 ``stdin`` 读取源码并编译为 module
    """
    source = sys.stdin.read()

    # 兼容相对于当前工作目录的导入
    sys.path.insert(0, os.getcwd())

    module_name = '__janim_main__'
    module = types.ModuleType(module_name)
    module.__file__ = STDIN_FILENAME

    # 让 inspect.getsourcelines 能从 linecache 读取 stdin 源码
    linecache.cache[STDIN_FILENAME] = (
        len(source),
        None,
        [line + '\n' for line in source.splitlines()],
        STDIN_FILENAME,
    )

    sys.modules[module_name] = module

    code = compile(source, STDIN_FILENAME, 'exec')
    exec(code, module.__dict__)

    return module


def get_module_from_file(file_name: str):
    """
    将给定的 ``file_name`` 读取为 module
    """
    if not os.path.exists(file_name):
        log.error(_('"{file_name}" doesn\'t exist').format(file_name=file_name))
        raise ExitException(EXITCODE_MODULE_NOT_FOUND)

    if not os.path.isfile(file_name):
        log.error(_('"{file_name}" isn\'t a file').format(file_name=file_name))
        raise ExitException(EXITCODE_NOT_FILE)

    # 兼容相对于源代码文件的导入
    sys.path.insert(0, os.path.abspath(os.path.dirname(file_name)))

    module_name = file_name.replace(os.sep, '.').replace('.py', '')
    loader = importlib.machinery.SourceFileLoader(module_name, file_name)
    module = loader.load_module()
    return module
