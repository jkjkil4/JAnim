import threading
from queue import Queue, Full

import pyaudio


class AudioPlayer:
    def __init__(self, framerate: int, channels: int):
        self.framerate = framerate
        self.channels = channels

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

            self.stream = p.open(format=pyaudio.paInt16,
                                 channels=self.channels,
                                 rate=self.framerate,
                                 output=True)

            try:
                while True:
                    data = self.queue.get()
                    self.stream.write(data)
            except OSError:
                pass
