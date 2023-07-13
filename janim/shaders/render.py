from __future__ import annotations
from typing import Optional
import os

from PySide6.QtCore import QObject
from PySide6.QtGui import QMatrix4x4, QVector2D, QVector3D
from PySide6.QtOpenGL import *
from OpenGL.GL import *

from janim.constants import *
from janim.utils.bezier import interpolate

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
    filename_to_shader_map: dict[str, ShaderProgram] = {}

    @staticmethod
    def get(filename: str) -> ShaderProgram:
        '''
        若 `filename` 对应着色器先前已创建过，则复用先前的对象，否则另外创建新的对象并记录
        '''
        if filename in ShaderProgram.filename_to_shader_map:
            return ShaderProgram.filename_to_shader_map[filename]
        
        shader = ShaderProgram(filename)
        ShaderProgram.filename_to_shader_map[filename] = shader
        return shader
    
    def __init__(self, path_name: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        
        for suffix, shader_type in self.keys:   # 遍历后缀读取着色器代码
            file_path = path_name + suffix
            if os.path.exists(file_path):
                if not self.addShaderFromSourceFile(shader_type, file_path):
                    print(f'Failed to compile "{file_path}"')
                    exit(1)
        
        if not self.link():
            print(f'Failed to link shader "{path_name}"')
            exit(1)

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


class DotCloudRenderer(Renderer):
    def init(self) -> None:
        self.shader = ShaderProgram.get('shaders/dotcloud')

        self.vao = glGenVertexArrays(1)
        self.vbo_points, self.vbo_rgbas, self.vbo_radii = glGenBuffers(3)
    
    def update(self, item) -> None:
        self.shader.bind()
        glBindVertexArray(self.vao)

        points = item.get_points()
        points_data_size = points.size * FLOAT_SIZE
        rgbas = item.get_rgbas()
        rgbas_data_size = rgbas.size * FLOAT_SIZE
        radii = item.get_radii()
        radii_data_size = radii.size * FLOAT_SIZE

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_points)
        glBufferData(GL_ARRAY_BUFFER, points_data_size, points, GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * FLOAT_SIZE, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_rgbas)
        glBufferData(GL_ARRAY_BUFFER, rgbas_data_size, rgbas, GL_STATIC_DRAW)
        glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, 4 * FLOAT_SIZE, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_radii)
        glBufferData(GL_ARRAY_BUFFER, radii_data_size, radii, GL_STATIC_DRAW)
        glVertexAttribPointer(2, 1, GL_FLOAT, GL_FALSE, FLOAT_SIZE, ctypes.c_void_p(0))
        glEnableVertexAttribArray(2)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

        glBindVertexArray(0)
    
    def render(self, item, data: RenderData) -> None:
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
        self.vao_fill = glGenVertexArrays(2)
        
        self.vbo_points = glGenBuffers(1)

        self.vbo_stroke_rgbas,  \
        self.vbo_stroke_width,  \
        self.vbo_joint_info = glGenBuffers(3)
        
        self.vbo_fill_rgbas = glGenBuffers(1)

    def update_stroke(self, item) -> None:        
        self.shader_stroke.bind()
        glBindVertexArray(self.vao_stroke)

        rgbas = item.get_rgbas()
        rgbas_data_size = rgbas.size * FLOAT_SIZE

        stroke = item.get_stroke_width()
        stroke_data_size = stroke.size * FLOAT_SIZE

        joint_info = item.get_joint_info()
        joint_info_data_size = joint_info.size * FLOAT_SIZE

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_points)
        # glBufferData(GL_ARRAY_BUFFER, points_data_size, points, GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * FLOAT_SIZE, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_stroke_rgbas)
        glBufferData(GL_ARRAY_BUFFER, rgbas_data_size, rgbas, GL_STATIC_DRAW)
        glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, 4 * FLOAT_SIZE, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_stroke_width)
        glBufferData(GL_ARRAY_BUFFER, stroke_data_size, stroke, GL_STATIC_DRAW)
        glVertexAttribPointer(2, 1, GL_FLOAT, GL_FALSE, FLOAT_SIZE, ctypes.c_void_p(0))
        glEnableVertexAttribArray(2)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_joint_info)
        glBufferData(GL_ARRAY_BUFFER, joint_info_data_size, joint_info, GL_STATIC_DRAW)
        glVertexAttribPointer(3, 3, GL_FLOAT, GL_FALSE, 3 * FLOAT_SIZE, ctypes.c_void_p(0))
        glEnableVertexAttribArray(3)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

        glBindVertexArray(0)

    def update_fill(self, item) -> None:
        self.shader_fill.bind()
        glBindVertexArray(self.vao_fill)

        rgbas = item.get_fill_rgbas()
        rgbas_data_size = rgbas.size * FLOAT_SIZE

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_points)
        # glBufferData(GL_ARRAY_BUFFER, points_data_size, points, GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * FLOAT_SIZE, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_fill_rgbas)
        glBufferData(GL_ARRAY_BUFFER, rgbas_data_size, rgbas, GL_STATIC_DRAW)
        glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, 4 * FLOAT_SIZE, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

        glBindVertexArray(0)

    def update(self, item) -> None:
        if item.points_count() < 3:
            return
        
        points = item.get_points()
        points_data_size = points.size * FLOAT_SIZE

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_points)
        glBufferData(GL_ARRAY_BUFFER, points_data_size, points, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        self.update_stroke(item)
        self.update_fill(item)

    def render_stroke(self, item, data: RenderData) -> None:
        self.shader_stroke.bind()
        self.shader_stroke.setFloat('anti_alias_width', data.anti_alias_width)
        self.shader_stroke.setMat4('view_matrix', data.view_matrix)
        self.shader_stroke.setMat4('proj_matrix', data.proj_matrix)
        self.shader_stroke.setMat4('wnd_matrix', data.wnd_matrix)
        self.shader_stroke.setVec3('vitem_unit_normal', *item.get_unit_normal())
        self.shader_stroke.setInt('joint_type', item.joint_type.value)

        glBindVertexArray(self.vao_stroke)
        glDrawArrays(GL_TRIANGLES, 0, item.points_count())
        glBindVertexArray(0)

    def render_fill(self, item, data: RenderData) -> None:
        triangulation = item.get_triangulation()

        self.shader_fill.bind()
        self.shader_fill.setFloat('anti_alias_width', data.anti_alias_width)
        self.shader_fill.setMat4('view_matrix', data.view_matrix)
        self.shader_fill.setMat4('proj_matrix', data.proj_matrix)
        self.shader_fill.setMat4('wnd_matrix', data.wnd_matrix)
        self.shader_fill.setVec3('vitem_unit_normal', *item.get_unit_normal())

        glBindVertexArray(self.vao_fill)
        glDrawElements(GL_TRIANGLES, len(triangulation), GL_UNSIGNED_INT, triangulation)
        glBindVertexArray(0)

    def render(self, item, data: RenderData) -> None:
        if item.points_count() < 3:
            return

        if item.stroke_behind_fill:
            self.render_stroke(item, data)
            self.render_fill(item, data)
        else:
            self.render_fill(item, data)
            self.render_stroke(item, data)