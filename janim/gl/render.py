from __future__ import annotations
from typing import Optional, Callable, Iterable

import os
import sys

from PySide6.QtCore import QObject
from PySide6.QtGui import QMatrix4x4, QVector2D, QVector3D
from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader
from OpenGL.GL import *

from janim.constants import *
from janim.items.dot_cloud import DotCloud
from janim.items.vitem import VItem
from janim.items.img_item import ImgItem
from janim.config import get_janim_dir

class ShaderProgram(QOpenGLShaderProgram):
    '''
    简单封装

    给定文件位置自动遍历后缀并读取着色器代码，
    例如传入 `shaders/dotcloud` 后，会自动读取 

    - `shaders/dotcloud.vert`
    - `shaders/dotcloud.geom`
    - `shaders/dotcloud.frag`

    的代码，若没有则缺省，但要能创建可用的着色器。

    使用 `ShaderProgram.get(filename)` 获取着色器对象可以便于复用
    '''

    keys = (    # 便于遍历后缀读取着色器代码
        ('.vert', QOpenGLShader.ShaderTypeBit.Vertex),
        ('.geom', QOpenGLShader.ShaderTypeBit.Geometry),
        ('.frag', QOpenGLShader.ShaderTypeBit.Fragment)
    )

    # 存储可复用的着色器对象
    filepath_to_shader_map: dict[str, ShaderProgram] = {}

    @staticmethod
    def get(filepath: str) -> ShaderProgram:
        '''
        若 `filename` 对应着色器先前已创建过，则复用先前的对象，否则另外创建新的对象并记录
        '''
        if filepath in ShaderProgram.filepath_to_shader_map:
            return ShaderProgram.filepath_to_shader_map[filepath]
        
        shader = ShaderProgram(os.path.join(get_janim_dir(), filepath))
        ShaderProgram.filepath_to_shader_map[filepath] = shader
        return shader
    
    @staticmethod
    def release_all() -> None:
        ShaderProgram.filepath_to_shader_map.clear()
    
    def __init__(self, path_name: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        
        for suffix, shader_type in self.keys:   # 遍历后缀读取着色器代码
            file_path = path_name + suffix
            if os.path.exists(file_path):
                if not self.addShaderFromSourceFile(shader_type, file_path):
                    print(f'Failed to compile "{file_path}"')
                    sys.exit(1)
        
        if not self.link():
            print(f'Failed to link shader "{path_name}"')
            sys.exit(1)

    def setMat4(self, name: str, mat: QMatrix4x4) -> None:
        self.setUniformValue(self.uniformLocation(name), mat)

    def setFloat(self, name: str, val: float) -> None:
        self.setUniformValue1f(self.uniformLocation(name), val)
    
    def setInt(self, name: str, val: int) -> None:
        self.setUniformValue1i(self.uniformLocation(name), val)
    
    def setVec2(self, name: str, val1: float, val2: float) -> None:
        self.setUniformValue(self.uniformLocation(name), QVector2D(val1, val2))

    def setVec3(self, name: str, val1: float, val2: float, val3: float) -> None:
        self.setUniformValue(self.uniformLocation(name), QVector3D(val1, val2, val3))

class RenderData:
    '''
    便于传递基本渲染数据信息
    '''
    def __init__(
        self,
        anti_alias_width: float,
        wnd_shape: tuple[float, float],
        camera_matrix: QMatrix4x4, 
        proj_matrix: QMatrix4x4,
        wnd_matrix: QMatrix4x4,
    ) -> None:
        self.anti_alias_width = anti_alias_width
        self.wnd_shape = wnd_shape
        self.view_matrix = camera_matrix
        self.proj_matrix = proj_matrix
        self.wnd_matrix = wnd_matrix

class Renderer:
    '''
    渲染器的基类

    渲染分为 `init`、`update`、`pre_render` 和 `render`

    `init`: 初始化渲染器对象时被调用

    `update`: 需要更新缓存对象数据时被调用，用于向GL传递物件数据的变化

    `pre_render`: 在渲染子物件前被调用，可以编写一些与子物件呈现效果有关的渲染代码

    `render`: 在子物件渲染后被调用，也是渲染当前对象的主要代码位置
    '''

    def __init__(self) -> None:
        self.initialized = False
        self.needs_update = True

        self.vertex_arrays_to_delete = []

    def prepare(self, item) -> None:
        if not self.initialized:
            self.init()
            self.initialized = True
        
        if self.needs_update:
            self.update(item)
            self.needs_update = False

    def init(self) -> None:
        pass

    def update(self, item) -> None:
        pass

    def pre_render(self, item, data: RenderData) -> None:
        pass
    
    def render(self, item, data: RenderData) -> None:
        pass

    def genVertexArrays(self, n: int):
        arrays = glGenVertexArrays(n)
        if isinstance(arrays, Iterable):
            self.vertex_arrays_to_delete.extend(arrays)
        else:
            self.vertex_arrays_to_delete.append(arrays)
        return arrays

    def __del__(self) -> None:
        try:
            if len(self.vertex_arrays_to_delete) > 0:
                glDeleteVertexArrays(len(self.vertex_arrays_to_delete), self.vertex_arrays_to_delete)
        except:
            pass


class Buffer:
    def __init__(
        self, 
        unit_len: int,
        buffer_type = GL_ARRAY_BUFFER, 
        dtype = GL_FLOAT,
        dsize = FLOAT_SIZE
    ) -> None:
        self.buffer = glGenBuffers(1)
        # self.needs_update = True
        self.unit_len = unit_len
        self.buffer_type = buffer_type
        self.dtype = dtype
        self.dsize = dsize

    def __del__(self) -> None:
        try:
            glDeleteBuffers(1, (self.buffer,))
        except:
            pass
    
    def pointer(self, index) -> None:
        glBindBuffer(self.buffer_type, self.buffer)
        glVertexAttribPointer(index, self.unit_len, self.dtype, GL_FALSE, self.unit_len * self.dsize, ctypes.c_void_p(0))
        glEnableVertexAttribArray(index)
        glBindBuffer(self.buffer_type, 0)

    def set_data(self, data: np.ndarray) -> None:   # TODO: set_data_if_needs
        # if not self.needs_update:
        #     return
        data_size = data.size * self.dsize
        glBindBuffer(self.buffer_type, self.buffer)
        glBufferData(self.buffer_type, data_size, data, GL_STATIC_DRAW)
        glBindBuffer(self.buffer_type, 0)

        # self.needs_update = False


class DotCloudRenderer(Renderer):
    def init(self) -> None:
        self.shader = ShaderProgram.get('shaders/dotcloud')

        self.vao = self.genVertexArrays(1)
        self.vbo_points = Buffer(3)
        self.vbo_rgbas = Buffer(4)
        self.vbo_radii = Buffer(1)

        self.shader.bind()
        glBindVertexArray(self.vao)

        self.vbo_points.pointer(0)
        self.vbo_rgbas.pointer(1)
        self.vbo_radii.pointer(2)

        glBindVertexArray(0)
    
    def update(self, item: DotCloud) -> None:
        self.vbo_points.set_data(item.get_points())
        self.vbo_rgbas.set_data(item.get_rgbas())
        self.vbo_radii.set_data(item.get_radii())
    
    def render(self, item: DotCloud, data: RenderData) -> None:
        self.shader.bind()

        self.shader.setFloat('anti_alias_width', data.anti_alias_width)
        self.shader.setMat4('view_matrix', data.view_matrix)
        self.shader.setMat4('proj_matrix', data.proj_matrix)
        self.shader.setMat4('wnd_matrix', data.wnd_matrix)

        glBindVertexArray(self.vao)
        glDrawArrays(GL_POINTS, 0, item.points_count())
        glBindVertexArray(0)

class VItemRenderer(Renderer):
    def init(self) -> None:
        self.shader_stroke = ShaderProgram.get('shaders/vitem_stroke')
        self.shader_fill = ShaderProgram.get('shaders/vitem_fill')

        self.vao_stroke,    \
        self.vao_fill = self.genVertexArrays(2)
        
        self.vbo_points = Buffer(3)

        self.vbo_stroke_rgbas = Buffer(4)
        self.vbo_stroke_width = Buffer(1)
        self.vbo_joint_info = Buffer(3)
        
        self.vbo_fill_rgbas = Buffer(4)

        self.ebo_fill_triangulation = Buffer(None, GL_ELEMENT_ARRAY_BUFFER, None, UINT_SIZE)

        self.shader_stroke.bind()
        glBindVertexArray(self.vao_stroke)
        
        self.vbo_points.pointer(0)
        self.vbo_stroke_rgbas.pointer(1)
        self.vbo_stroke_width.pointer(2)
        self.vbo_joint_info.pointer(3)
        
        self.shader_fill.bind()
        glBindVertexArray(self.vao_fill)

        self.vbo_points.pointer(0)
        self.vbo_fill_rgbas.pointer(1)

        glBindVertexArray(0)

    def update_stroke(self, item: VItem) -> None:
        if not item.get_rgbas_visible():
            return
        self.vbo_stroke_rgbas.set_data(item.get_rgbas())
        self.vbo_stroke_width.set_data(item.get_stroke_width())
        self.vbo_joint_info.set_data(item.get_joint_info())

    def update_fill(self, item: VItem) -> None:
        if not item.get_fill_rgbas_visible():
            return
        self.vbo_fill_rgbas.set_data(item.get_fill_rgbas())
        self.ebo_fill_triangulation.set_data(item.get_triangulation())

    def update(self, item: VItem) -> None:
        if item.points_count() < 3:
            return
        
        self.vbo_points.set_data(item.get_points())

        self.update_stroke(item)
        self.update_fill(item)

    def render_stroke(self, item: VItem, data: RenderData, z_offset: float) -> None:
        if not item.get_rgbas_visible():
            return
        
        self.shader_stroke.bind()
        self.shader_stroke.setFloat('anti_alias_width', data.anti_alias_width)
        self.shader_stroke.setMat4('view_matrix', data.view_matrix)
        self.shader_stroke.setMat4('proj_matrix', data.proj_matrix)
        self.shader_stroke.setMat4('wnd_matrix', data.wnd_matrix)
        self.shader_stroke.setVec3('vitem_unit_normal', *item.get_unit_normal())
        self.shader_stroke.setInt('joint_type', item.joint_type.value)
        self.shader_stroke.setFloat('z_offset', z_offset)

        glBindVertexArray(self.vao_stroke)
        glDrawArrays(GL_TRIANGLES, 0, item.points_count())
        glBindVertexArray(0)

    def render_fill(self, item: VItem, data: RenderData) -> None:
        if not item.get_fill_rgbas_visible():
            return
        
        triangulation = item.get_triangulation()

        self.shader_fill.bind()
        # self.shader_fill.setFloat('anti_alias_width', data.anti_alias_width)
        self.shader_fill.setMat4('view_matrix', data.view_matrix)
        self.shader_fill.setMat4('proj_matrix', data.proj_matrix)
        self.shader_fill.setMat4('wnd_matrix', data.wnd_matrix)
        self.shader_fill.setVec3('vitem_unit_normal', *item.get_unit_normal())

        glBindVertexArray(self.vao_fill)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo_fill_triangulation.buffer)
        glDrawElements(GL_TRIANGLES, len(triangulation), GL_UNSIGNED_INT, None)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def render(self, item: VItem, data: RenderData) -> None:
        if item.points_count() < 3:
            return

        if item.stroke_behind_fill:
            self.render_stroke(item, data, -1e-4)
            self.render_fill(item, data)
        else:
            self.render_fill(item, data)
            self.render_stroke(item, data, 1e-4)

class ImgItemRenderer(Renderer):
    tex_coord = np.array([
        [1.0, 0.0], # 右上
        [1.0, 1.0], # 右下
        [0.0, 1.0], # 左下
        [0.0, 0.0]  # 左上
    ], dtype=np.float32)

    idx = np.array([
        0, 1, 3,
        1, 2, 3
    ], dtype='uint')

    def init(self) -> None:
        self.shader = ShaderProgram.get('shaders/image')

        self.vao = self.genVertexArrays(1)

        self.vbo_points = Buffer(3)
        self.vbo_rgbas = Buffer(4)
        self.vbo_texcoords = Buffer(2)

        self.shader.bind()
        glBindVertexArray(self.vao)

        self.vbo_points.pointer(0)
        self.vbo_rgbas.pointer(1)
        self.vbo_texcoords.pointer(2)
        self.vbo_texcoords.set_data(self.tex_coord)

        glBindVertexArray(0)

    def update(self, item: ImgItem) -> None:
        self.vbo_points.set_data(item.get_points())
        self.vbo_rgbas.set_data(item.get_rgbas())

    def render(self, item: ImgItem, data: RenderData) -> None:
        glActiveTexture(GL_TEXTURE0)
        item.texture.bind()

        self.shader.bind()

        self.shader.setMat4('view_matrix', data.view_matrix)
        self.shader.setMat4('proj_matrix', data.proj_matrix)
        self.shader.setMat4('wnd_matrix', data.wnd_matrix)

        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, self.idx)
        glBindVertexArray(0)

