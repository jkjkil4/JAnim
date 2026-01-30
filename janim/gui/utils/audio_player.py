import threading
from queue import Empty, Full, Queue

import sounddevice as sd


class AudioPlayer:
    def __init__(self, framerate: int, channels: int, fps: int):
        self._framerate = framerate
        self._channels = channels

        self.empty_data = bytes(framerate // fps * 2 * channels)

        self.queue: Queue[bytes] = Queue(maxsize=2)
        self.quit_event = threading.Event()

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def write(self, data: bytes):
        try:
            self.queue.put(data, block=False)
        except Full:
            pass

    def close(self) -> None:
        self.quit_event.set()

    def _run(self):
        while not self.quit_event.is_set():
            stream = sd.RawOutputStream(
                samplerate=self._framerate,
                channels=self._channels,
                dtype='int16',
            )
            stream.start()

            try:
                while not self.quit_event.is_set():
                    try:
                        data = self.queue.get(timeout=1)
                    except Empty:
                        # 在一些设备上，当 stream 长时间未收到数据时，下次 write 会卡顿一会
                        # 所以这里定期使用空数据保持其活跃
                        data = self.empty_data
                    stream.write(data)
            except sd.PortAudioError:
                # 当音频设备被拔出后，会造成 Error，此时重启 stream
                pass
