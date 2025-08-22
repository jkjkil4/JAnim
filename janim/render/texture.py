import os
import weakref

import moderngl as mgl
from PIL import Image

from janim.render.base import Renderer
from janim.utils.file_ops import find_file

filepath_to_img_map: dict[tuple[str, float], Image.Image] = {}


def get_img_from_file(file_path: str) -> Image.Image:
    file_path = find_file(file_path)
    mtime = os.path.getmtime(file_path)
    key = (file_path, mtime)

    img = filepath_to_img_map.get(key, None)
    if img is not None:
        return img
    img = Image.open(file_path).convert('RGBA')
    filepath_to_img_map[key] = img
    return img


# 存在新的 Image 对象与先前已经释放的 Image 对象具有相同 id 的可能
# 所以这里使用 ref，从而检查 Image 对象是否被释放掉
img_to_texture_map: dict[tuple[mgl.Context, int], tuple[mgl.Texture, weakref.ref]] = {}


def get_texture_from_img(img: Image.Image) -> mgl.Texture:
    ctx = Renderer.data_ctx.get().ctx
    key = (ctx, id(img))
    texture, ref = img_to_texture_map.get(key, (None, None))
    if texture is not None and ref() is not None:
        return texture
    texture = ctx.texture(
        size=img.size,
        components=len(img.getbands()),
        data=img.tobytes()
    )
    texture.repeat_x = False
    texture.repeat_y = False
    img_to_texture_map[key] = (texture, weakref.ref(img))
    return texture
