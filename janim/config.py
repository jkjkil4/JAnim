import argparse
import sys, os
import importlib
import inspect
import yaml

from janim.logger import log
from janim.utils.dict_ops import merge_dicts_recursively

def parse_cli() -> argparse.Namespace:
    try:
        parser = argparse.ArgumentParser()
        module_location = parser.add_mutually_exclusive_group()
        module_location.add_argument(
            'file',
            nargs='?',
            help='Path to file holding the python code for the scene'
        )
        parser.add_argument(
            'scene_names',
            nargs='*',
            help='Name of the Scene class you want to see'
        )
        parser.add_argument(
            "-a", "--write_all",
            action="store_true",
            help="Write all the scenes from a file",
        )
        parser.add_argument(
            "--config",
            action="store_true",
            help="Guide for automatic configuration",
        )
        parser.add_argument(
            "-c", "--color",
            help="Background color",
        )
        parser.add_argument(
            "--config_file",
            help="Path to the custom configuration file",
        )
        parser.add_argument(
            "-v", "--version",
            action="store_true",
            help="Display the version of janim"
        )
        return parser.parse_args()
    except argparse.ArgumentError as err:
        log.error(str(err))
        sys.exit(2)


def get_janim_dir() -> str:
    janim_module = importlib.import_module('janim')
    janim_dir = os.path.dirname(inspect.getabsfile(janim_module))
    return os.path.abspath(os.path.join(janim_dir, '..'))


def get_configuration(args: argparse.Namespace):
    # 默认配置路径 与 自定义配置路径
    default_config_file = os.path.join(get_janim_dir(), 'janim', 'default_config.yml')
    custom_config_file = args.config_file or 'custom_config.yml'

    # 对配置路径进行提示
    default_config_exists = os.path.exists(default_config_file)
    custom_config_exists = os.path.exists(custom_config_file)

    if not default_config_exists:
        log.error(f'Cannot find "{default_config_file}", please check the integrity of JAnim')
        sys.exit(2)
    
    if not custom_config_exists:
        log.info(f"Using the default configuration file, which you can modify in `{default_config_file}`")
        log.info(
            "If you want to create a local configuration file, you can create a file named"
            " `custom_config.yml`, or run `janim --config`"
        )
    
    # 读取默认配置
    with open(default_config_file, 'r') as file:
        config = yaml.safe_load(file)
    
    # 读取自定义配置
    if custom_config_exists:
        with open(custom_config_file, 'r') as file:
            custom_config = yaml.safe_load(file)
            # 将 custom_config 的内容合并至 config 中
            # 以达到 自定义配置 覆盖 默认配置 的目的
            config = merge_dicts_recursively(
                config,
                custom_config
            )

    return config

def init_customization() -> None:
    pass # TODO: init_customization
