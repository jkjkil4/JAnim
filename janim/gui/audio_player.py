import threading
from queue import Empty, Full, Queue

import pyaudio


class AudioPlayer:
    def __init__(self, framerate: int, channels: int, fps: int):
        self.framerate = framerate
        self.channels = channels

        self.empty_data = bytes(self.framerate // fps)

        self.queue: Queue = Queue(maxsize=2)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def write(self, data: bytes):
        try:
            self.queue.put(data, block=False)
        except Full:
            pass

    def _run(self):
        while True:
            p = pyaudio.PyAudio()

            stream = p.open(format=pyaudio.paInt16,
                            channels=self.channels,
                            rate=self.framerate,
                            output=True)

            try:
                while True:
                    try:
                        data = self.queue.get(timeout=1)
                    except Empty:
                        # 由于当 stream 长时间未收到数据时，下次 write 会卡顿一会
                        # 所以这里定期使用空数据保持其活跃
                        data = self.empty_data
                    stream.write(data)
            except OSError:
                # 当音频设备被拔出后，会造成 OSError，此时重启 stream
                pass
