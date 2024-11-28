import importlib.util
import inspect
import os
import platform
import subprocess as sp


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
    from janim.utils.config import Config
    return guarantee_existence(os.path.join(Config.get.temp_dir, 'Typst'))


def readall(filepath: str) -> str:
    '''
    从文件中读取所有字符
    '''
    with open(filepath, 'rt', encoding='utf-8') as f:
        return f.read()


def find_file_in_path(path: str, file_path: str) -> str | None:
    joined_filepath = os.path.join(path, file_path)
    return joined_filepath if os.path.exists(joined_filepath) else None


def find_file_in_asset_dir(prefix: str, file_path: str) -> str | None:
    from janim.utils.config import Config

    asset_dir = Config.get.asset_dir
    if isinstance(asset_dir, str):
        # in asset_dir
        found_path = find_file_in_path(os.path.join(prefix, asset_dir), file_path)
        if found_path is not None:
            return found_path
    else:
        for dir in asset_dir:
            found_path = find_file_in_path(os.path.join(prefix, dir), file_path)
            if found_path is not None:
                return found_path

    return None


def find_file(file_path: str) -> str:
    # find in default path
    found_path = find_file_in_path('', file_path)
    if found_path is not None:
        return found_path

    # find relative to source file (relative_path)
    from janim.anims.timeline import Timeline

    timeline = Timeline.get_context(raise_exc=False)
    relative_path = None if timeline is None else os.path.dirname(inspect.getfile(timeline.__class__))
    if relative_path is not None:
        found_path = find_file_in_path(relative_path, file_path)
        if found_path is not None:
            return found_path

    # find in asset_dir
    found_path = find_file_in_asset_dir('', file_path)
    if found_path is not None:
        return found_path

    # find in relative_path + asset_dir
    if relative_path is not None:
        found_path = find_file_in_asset_dir(relative_path, file_path)
        if found_path is not None:
            return found_path

    # not found
    raise FileNotFoundError(file_path)


def open_file(file_path: str) -> None:
    '''
    打开指定的文件
    '''
    current_os = platform.system()
    if current_os == "Windows":
        os.startfile(file_path)
    else:
        commands = []
        if current_os == "Linux":
            commands.append("xdg-open")
        elif current_os.startswith("CYGWIN"):
            commands.append("cygstart")
        else:  # Assume macOS
            commands.append("open")

        commands.append(file_path)

        FNULL = open(os.devnull, 'w')
        sp.call(commands, stdout=FNULL, stderr=sp.STDOUT)
        FNULL.close()
