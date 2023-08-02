import inspect
import sys, os
import argparse
import importlib.util

from janim.scene.scene import Scene
from janim.logger import log


class BlankScene(Scene):
    pass


def is_child_scene(obj, module):
    if not inspect.isclass(obj):
        return False
    if not issubclass(obj, Scene):
        return False
    if obj == Scene:
        return False
    if not obj.__module__.startswith(module.__name__):
        return False
    return True

def get_module(file_name: str):
    if file_name is None:
        return None
    module_name = file_name.replace(os.sep, '.').replace('.py', '')
    spec = importlib.util.spec_from_file_location(module_name, file_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prompt_user_for_choice(scene_classes):
    name_to_class = {}
    max_digits = len(str(len(scene_classes)))
    for idx, scene_class in enumerate(scene_classes, start=1):
        name = scene_class.__name__
        print(f"{str(idx).zfill(max_digits)}: {name}")
        name_to_class[name] = scene_class
    try:
        user_input = input(
            "\nThat module has multiple scenes, "
            "which ones would you like to render?"
            "\nScene Name or Number: "
        )
        return [
            name_to_class[split_str] if not split_str.isnumeric() else scene_classes[int(split_str) - 1]
            for split_str in user_input.replace(" ", "").split(",")
        ]
    except IndexError:
        log.error("Invalid scene number")
        sys.exit(2)
    except KeyError:
        log.error("Invalid scene name")
        sys.exit(2)
    except EOFError:
        sys.exit(1)


def get_scenes_to_render(scene_classes, args, config):
    if args.write_all:
        return [sc() for sc in scene_classes]

    result = []
    for scene_name in args.scene_names:
        found = False
        for scene_class in scene_classes:
            if scene_class.__name__ == scene_name:
                scene = scene_class()
                result.append(scene)
                found = True
                break
        if not found and (scene_name != ""):
            log.error(f"No scene named {scene_name} found")
    if result:
        return result
    if len(scene_classes) == 1:
        result = [scene_classes[0]]
    else:
        result = prompt_user_for_choice(scene_classes)
    return [scene_class() for scene_class in result]


def get_scene_classes_from_module(module):
    if hasattr(module, "SCENES_IN_ORDER"):
        return module.SCENES_IN_ORDER
    else:
        return [
            member[1]
            for member in inspect.getmembers(
                module,
                lambda x: is_child_scene(x, module)
            )
        ]


def main(args: argparse.Namespace, config: dict):
    module = get_module(args.file)
    
    if module is None:
        # If no module was passed in, just play the blank scene
        return [BlankScene()]

    all_scene_classes = get_scene_classes_from_module(module)
    scenes = get_scenes_to_render(all_scene_classes, args, config)
    return scenes
