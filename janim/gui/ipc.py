import json
import sys
import threading
from typing import Callable, Optional

from PySide6.QtCore import QByteArray, QObject, Signal
from PySide6.QtNetwork import QHostAddress, QUdpSocket

from janim.locale.i18n import get_local_strings
from janim.logger import log

_ = get_local_strings('anim_viewer')


class IPCConnection(QObject):
    """
    通信策略基类
    """
    # 当收到合法的 Janim JSON 数据包 ({'janim': ...}) 时发出此信号
    message_received = Signal(dict)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

    def send(self, data: dict) -> None:
        """发送数据 (data 应为完整的 dict，包含 'janim' key)"""
        raise NotImplementedError

    def cleanup(self) -> None:
        """清理资源 (停止线程/关闭Socket)"""
        pass


class StdioConnection(IPCConnection):
    """
    基于标准输入输出 (Stdio) 的通信实现
    用于 Electron 集成
    """
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._running = True
        # 使用 daemon 线程，防止主程序退出时线程卡死
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        log.info(_('Listening on stdio for IPC command...'))

    def _listen_loop(self) -> None:
        while self._running:
            try:
                # 阻塞读取 stdin，直到收到换行符
                line = sys.stdin.readline()
                if not line:  # EOF (通常意味着父进程 Electron 关闭了管道)
                    break
                # 解析并验证是否为 JSON
                data = json.loads(line.strip())
                if isinstance(data, dict):
                    self.message_received.emit(data)
            except json.JSONDecodeError:
                pass  # 忽略非 JSON 的日志输出
            except Exception:
                break

    def send(self, data: dict) -> None:
        try:
            # flush=True 至关重要，否则 Electron 可能无法及时收到数据
            print(json.dumps(data), flush=True)
        except Exception:
            pass

    def cleanup(self) -> None:
        self._running = False


class UdpConnection(IPCConnection):
    """
    基于 UDP 的通信实现
    用于 VSCode 插件交互 (Legacy)
    """
    def __init__(self,
                 search_port: int,
                 file_path: str,
                 window_title_callback: Optional[Callable[[str], None]] = None,
                 parent: Optional[QObject] = None):
        super().__init__(parent)

        self.file_path = file_path
        self.clients: set[tuple[QHostAddress, int]] = set()

        # 1. 初始化 Socket
        self.socket = QUdpSocket(self)
        self.shared_socket = QUdpSocket(self)

        # 2. 绑定发现端口 (Shared) - 用于插件发现此实例
        if 1024 <= search_port <= 65535:
            ret = self.shared_socket.bind(
                QHostAddress.SpecialAddress.LocalHost,
                search_port,
                QUdpSocket.BindFlag.ShareAddress | QUdpSocket.BindFlag.ReuseAddressHint
            )
            if ret:
                self.shared_socket.readyRead.connect(self.on_shared_ready_read)
                log.info(_('Searching port has been opened at {port}').format(port=search_port))
            else:
                log.warning(_('Failed to open searching port at {port}').format(port=search_port))
        else:
            log.warning(_('Searching port {port} is invalid').format(port=search_port))

        # 3. 绑定交互端口 (OS 自动分配空闲端口)
        self.socket.bind()
        self.socket.readyRead.connect(self.on_ready_read)

        local_port = self.socket.localPort()
        log.info(_('Interactive port has been opened at {port}').format(port=local_port))

        # 回调通知主窗口修改标题 (显示端口号)
        if window_title_callback:
            window_title_callback(f" [{local_port}]")

    def on_shared_ready_read(self) -> None:
        """处理发现请求 (Find)"""
        while self.shared_socket.hasPendingDatagrams():
            datagram = self.shared_socket.receiveDatagram()
            try:
                data = json.loads(datagram.data().toStdString())
                if data.get('janim', {}).get('type') == 'find':
                    # 直接在这里回复 find_re
                    self._reply_find(datagram.senderAddress(), datagram.senderPort())
            except Exception:
                pass

    def _reply_find(self, address: QHostAddress, port: int) -> None:
        msg = json.dumps({
            'janim': {
                'type': 'find_re',
                'data': {
                    'port': self.socket.localPort(),
                    'file_path': self.file_path
                }
            }
        })
        self.socket.writeDatagram(QByteArray.fromStdString(msg), address, port)

    def on_ready_read(self) -> None:
        """处理交互指令"""
        while self.socket.hasPendingDatagrams():
            datagram = self.socket.receiveDatagram()
            try:
                tree = json.loads(datagram.data().toStdString())
                janim_data = tree.get('janim', {})

                # UDP 特有逻辑：注册客户端地址
                if janim_data.get('type') == 'register_client':
                    self.clients.add((datagram.senderAddress(), datagram.senderPort()))

                self.message_received.emit(tree)
            except Exception:
                pass

    def send(self, data: dict) -> None:
        msg = QByteArray.fromStdString(json.dumps(data))
        for client in self.clients:
            self.socket.writeDatagram(msg, *client)