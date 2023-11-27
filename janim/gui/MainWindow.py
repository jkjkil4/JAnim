import sys
import traceback

from PySide6.QtCore import Qt, QMargins, QByteArray
from PySide6.QtGui import QCloseEvent, QVector4D, QMatrix4x4
from PySide6.QtWidgets import QWidget, QApplication, QStackedLayout, QLabel

from janim.gui.GLWidget import GLWidget
from janim.gui.Overlay import Overlay
from janim.scene.scene import Scene
from janim.items.item import Item

from janim.gl.texture import Texture
from janim.gl.render import ShaderProgram

from janim.config import get_configuration
from janim.logger import log

class MainWindow(QWidget):
    def __init__(self, scene: Scene, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.glwidget = GLWidget(scene, self)
        self.overlay = Overlay(self.glwidget)
        self.isEmbed = False
        self.isClosed = False

        self.stkLayout = QStackedLayout()
        self.stkLayout.setContentsMargins(QMargins())
        self.stkLayout.setSpacing(0)
        self.stkLayout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.stkLayout.addWidget(self.glwidget)
        self.stkLayout.addWidget(self.overlay)
        self.setLayout(self.stkLayout)

        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle()
    
    def setWindowTitle(self, text: str = '') -> None:
        super().setWindowTitle('JAnim' if len(text) == 0 else 'JAnim - ' + text)

    def moveToPosition(self) -> None:
        conf = get_configuration()
        window_position = conf['window']['position']
        window_monitor = conf['window']['monitor']

        if len(window_position) != 2 or window_position[0] not in 'UOD' or window_position[1] not in 'LOR':
            log.error(f'window.position has wrong argument "{window_position}".')
            sys.exit(2)
        
        screens = QApplication.screens()
        if window_monitor < len(screens):
            screen = screens[window_monitor]
        else:
            screen = screens[0]
            log.warning(f'window.monitor has invaild value {window_monitor}, please use 0~{len(screens) - 1} instead.')
        screen_size = screen.availableSize()
        
        if window_position[1] == 'O':
            width = screen_size.width()
            x = 0
        else:
            width = screen_size.width() / 2
            x = 0 if window_position[1] == 'L' else width
        
        if window_position[0] == 'O':
            height = screen_size.height()
            y = 0
        else:
            height = screen_size.height() / 2
            y = 0 if window_position[0] == 'U' else height
        
        self.move(x, y)
        self.resize(width, height)

    #region socket

    def enableSocket(self) -> None:
        '''
        创建从网络接口接收数据的 UdpSocket，
        以接收从 vscode 插件 janim-toolbox 发送的指令
        '''
        from PySide6.QtNetwork import QUdpSocket

        self.sharedSocket = QUdpSocket()
        print(self.sharedSocket.bind(40565, QUdpSocket.BindFlag.ShareAddress | QUdpSocket.BindFlag.ReuseAddressHint))
        self.sharedSocket.readyRead.connect(self.onSharedReadyRead)

        self.socket = QUdpSocket()
        self.socket.bind()
        self.stored_states = 0

        self.socket.readyRead.connect(self.onReadyRead)

        self.glwidget.scene.save_state('_d_orig')

        self.displayingCIV: list[QLabel] = []

        log.info(f'调试端口已在 {self.socket.localPort()} 开启')
        self.setWindowTitle(str(self.socket.localPort()))
        self.isEmbed = True
        self.update()

    def onSharedReadyRead(self) -> None:
        import json

        while self.sharedSocket.hasPendingDatagrams():
            datagram = self.sharedSocket.receiveDatagram()
            try:
                tree = json.loads(datagram.data().toStdString())
                assert('janim' in tree)

                janim = tree['janim']
                cmdtype = janim['type']

                if cmdtype == 'find':
                    msg = json.dumps(dict(
                        janim=dict(
                            type='find_re',
                            data=self.socket.localPort()
                        )
                    ))
                    self.socket.writeDatagram(
                        QByteArray.fromStdString(msg), 
                        datagram.senderAddress(), 
                        datagram.senderPort()
                    )
            except:
                traceback.print_exc()

    def onReadyRead(self) -> None:
        import json

        # TODO: 添加安全措施，防止远程执行恶意代码
        while self.socket.hasPendingDatagrams():
            datagram = self.socket.receiveDatagram()
            try:
                tree = json.loads(datagram.data().toStdString())
                assert('janim' in tree)
                
                janim = tree['janim']
                cmdtype = janim['type']

                # 执行代码
                if cmdtype == 'exec_code':
                    self.glwidget.scene.save_state(f'_d_{self.stored_states}')
                    self.stored_states += 1

                    # 计算代码的缩进量
                    lines = janim['data'].splitlines()
                    indent = 0
                    for line in lines:
                        line_indent = 0
                        for char in line:
                            if char not in '\t ':
                                break
                            line_indent += 1

                        indent = line_indent if indent == 0 else min(indent, line_indent)

                    # 执行删除缩进后的代码
                    self.glwidget.scene.execute('\n'.join(line[indent:] for line in lines))
                    log.info('代码执行完成')
                    self.glwidget.updateFlag = True

                # 撤销代码
                elif cmdtype == 'undo_code':
                    if self.stored_states > 0:
                        self.stored_states -= 1
                        self.glwidget.scene.restore(f'_d_{self.stored_states}')
                        log.info(f'已撤销代码')
                    else:
                        self.glwidget.scene.restore(f'_d_orig')
                        log.info('已回到初始状态')
                    self.glwidget.updateFlag = True

                # 查看子物件序号
                elif cmdtype == 'display_children_index':
                    # 清空先前显示的序号
                    for label in self.displayingCIV:
                        self.overlay.removeWidget(label)
                    self.displayingCIV.clear()

                    # 得到需要查看的物件
                    name: str = janim['data']

                    if len(name) != 0:
                        try:
                            item = eval(name, self.glwidget.scene.embed_globals)
                        except:
                            log.warning(f'Cannot find "{name}"')
                            return
                        
                        if not isinstance(item, Item):
                            log.warning(f'Found "{name}"{type(item)}, but it\'s not an instance of Item')
                            return
                        
                        # 得到变换至屏幕坐标的矩阵
                        camera = self.glwidget.scene.camera

                        matrix = QMatrix4x4()
                        matrix.setToIdentity()
                        camera.apply_perspective_to_matrix(matrix)
                        matrix = matrix * camera.compute_view_matrix()
                        
                        # 遍历子物件，显示序号
                        for i, subitem in enumerate(item):
                            wnd_pos: QVector4D = matrix.map(QVector4D(*subitem.get_center(), 1))

                            label = QLabel(str(i))
                            label.setStyleSheet(
                                'color: white;'
                                'background: rgba(0,0,0,180);'
                                'padding: 2px;'
                                'font: bold 10px;'
                            )
                            self.displayingCIV.append(label)
                            self.overlay.addWidget(
                                label, 
                                (wnd_pos.x() / wnd_pos.w(), wnd_pos.y() / wnd_pos.w()), 
                                Qt.AlignmentFlag.AlignCenter
                            )
            except:
                traceback.print_exc()

    #endregion

    def closeEvent(self, event: QCloseEvent) -> None:
        self.isClosed = True
        self.glwidget.scene.loop_helper.event_loop.quit()
        Texture.release_all()
        ShaderProgram.release_all()
        super().closeEvent(event)

    def emit_frame(self) -> None:
        self.glwidget.update()

    def finish(self) -> None:
        pass
        
    
