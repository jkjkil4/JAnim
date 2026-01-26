import threading

import numpy as np
import sounddevice as sd

from janim.locale.i18n import get_translator

_ = get_translator('janim.gui.utils.audio_player')


class AudioPlayer:
    def __init__(self, framerate: int, channels: int, fps: int):
        self._framerate = framerate
        self._channels = channels
        self._fps = fps
        self._blocksize = self._framerate // self._fps

        self._dropsize = self._blocksize * 2
        self._buffersize = self._blocksize * 8
        self._buffer = np.empty((self._buffersize, self._channels), dtype=np.int16)
        self._pending_frames: int = 0
        self._burst_cooldown: int = 0
        self._lock = threading.Lock()

        self._closed = False
        self._start_stream()

    def _start_stream(self) -> None:
        def audio_callback(outdata: np.ndarray, frames: int, time, status: sd.CallbackFlags):
            # 策略：
            # 如果此时 pending 未满 frames，则将 outdata 的前面填充为 pending 的数据，其余填 0； (1)
            # 否则，将 pending 前 frames 的数据消耗掉，保留剩余的数据 (2)
            #
            # 注：frames 正常来说就是 blocksize

            with self._lock:
                if self._pending_frames < frames:
                    # (1)
                    outdata[:self._pending_frames] = self._buffer[:self._pending_frames]
                    outdata[self._pending_frames:] = 0
                    self._pending_frames = 0
                else:
                    # (2)
                    outdata[:] = self._buffer[:frames]
                    if self._pending_frames == frames:
                        self._pending_frames = 0
                    else:
                        last = self._pending_frames - frames
                        self._buffer[:last] = self._buffer[frames:self._pending_frames]
                        self._pending_frames = last

        self._stream = sd.OutputStream(
            samplerate=self._framerate,
            channels=self._channels,
            dtype='int16',
            blocksize=self._blocksize,
            latency='low',
            callback=audio_callback
        )
        self._stream.start()

    def play(self, array: np.ndarray) -> None:
        # 当音频设备被拔出后，会使 stream 结束，此时重启 stream
        if not self._stream.active and not self._closed:
            self._stream.stop()
            self._stream.close()
            self._start_stream()

        # 在非跳帧的情况下，array 长度总是和 blocksize 不相上下，而在负载情况下并处于跳帧时，会一次性收到成倍的数据
        # 因此判断大于 1.5 倍的 blocksize 即为突发输入
        is_burst_input = len(array) > (self._blocksize * 1.5)
        if is_burst_input:
            self._burst_cooldown = 3    # 用于过滤，如果连续三帧不突发，才重新缩紧 limitsize
        elif self._burst_cooldown > 0:
            self._burst_cooldown -= 1

        with self._lock:
            # 策略：
            #
            # 如果此时还没有达到 dropsize，则允许填充到 buffersize 的大小， (1)
            # 因为可能过两帧就可以被正常消耗掉，blocksize ~ buffersize 之间的就是允许的额外暂存量
            #
            # 如果此时装满了一个 blocksize，则只允许填充到 blocksize 的大小， (2)
            # 因为说明这下已经溢出到暂存了整个 blocksize 的数据的情况了，这整个 blocksize 的数据都没有被及时消耗掉，我们要及时丢弃过早的数据
            #
            # 通过以上的两个情况确定能填充到的大小 limitsize 之后，
            # 如果已有的 pending_frames 加上 array 的总长度没有超过 limitsize，则将 array 追加到已有数据的后面； (3)
            # 否则，如果总长度超过了 limitsize，则弹出最早的那段数据，使得 array 追加后，最终的总长度刚好触及 limitsize (4)
            #
            # 注：因为我们可以保证 array 长度总是和 blocksize 不相上下，从而 buffer 的内存平移总是很小，所以可以不用环形缓冲

            if self._pending_frames < self._dropsize or self._burst_cooldown > 0:   # 对于突发情况，放宽 limitsize
                # (1)
                limitsize = self._buffersize
            else:
                # (2)
                limitsize = self._blocksize

            # part1 = '#' * int(self._pending_frames / self._buffersize * 60)
            # part2 = ' ' * (60 - len(part1))
            # print(
            #     int(is_burst_input),
            #     self._burst_cooldown,
            #     f'{self._pending_frames:>4}/{limitsize:>4}', f'[{part1}{part2}]'
            # )

            totalsize = self._pending_frames + len(array)
            if totalsize <= limitsize:
                # (3)
                self._buffer[self._pending_frames:totalsize] = array
                self._pending_frames = totalsize
            else:
                # (4)
                offset = totalsize - limitsize
                if offset <= self._pending_frames:
                    truncated_size = self._pending_frames - offset  # pending 部分截断后剩余的长度
                    self._buffer[:truncated_size] = self._buffer[offset:self._pending_frames]
                    self._buffer[truncated_size:limitsize] = array
                else:
                    truncate_size = offset - self._pending_frames   # array 需要截断的长度
                    self._buffer[:limitsize] = array[truncate_size:]
                self._pending_frames = limitsize

    def close(self) -> None:
        self._closed = True
        self._stream.stop()
        self._stream.close()
