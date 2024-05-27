import os

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


img_to_texture_map: dict[tuple[mgl.Context, int], mgl.Texture] = {}


def get_texture_from_img(img: Image.Image) -> mgl.Texture:
    ctx = Renderer.data_ctx.get().ctx
    key = (ctx, id(img))
    texture = img_to_texture_map.get(key, None)
    if texture is not None:
        return texture
    texture = ctx.texture(
        size=img.size,
        components=len(img.getbands()),
        data=img.tobytes()
    )
    texture.repeat_x = False
    texture.repeat_y = False
    img_to_texture_map[key] = texture
    return texture
