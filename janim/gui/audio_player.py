import threading
from queue import Queue, Full

import pyaudio


class AudioPlayer:
    def __init__(self, framerate: int):
        self.framerate = framerate

        self.queue: Queue = Queue(maxsize=2)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def write(self, data: bytes):
        try:
            self.queue.put(data, block=False)
        except Full:
            pass

    def _run(self):
        p = pyaudio.PyAudio()

        self.stream = p.open(format=pyaudio.paInt16,
                             channels=1,
                             rate=self.framerate,
                             output=True)

        while True:
            data = self.queue.get()
            self.stream.write(data)
