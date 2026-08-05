import os
import subprocess as sp

import janim.examples as examples
from janim.render.writer import VideoWriter
from janim.utils.config import Config

dir = os.path.dirname(__file__)


def write_video(fps1: int, fps2: int) -> None:
    file_video1 = os.path.join(dir, 'video1.mp4')
    file_video2 = os.path.join(dir, 'video2.mp4')
    file_txt = os.path.join(dir, 'file.txt')
    file_out = os.path.join(dir, f'VFR-fps{fps1}-fps{fps2}.mp4')

    with Config(fps=fps1):
        VideoWriter.writes(examples.TextExample().build(), file_video1)
    with Config(fps=fps2):
        VideoWriter.writes(examples.RotatingPieExample().build(), file_video2)

    with open(file_txt, 'wt') as f:
        f.write(f"file '{file_video1}'\nfile '{file_video2}'")

    sp.run(
        [
            "ffmpeg",
            "-i", file_video1,
            "-i", file_video2,
            "-filter_complex",
            (
                "[0:v]setpts=PTS-STARTPTS[v0];"
                "[1:v]setpts=PTS-STARTPTS[v1];"
                "[v0][v1]concat=n=2:v=1:a=0[v]"
            ),
            "-map", "[v]",
            "-fps_mode", "vfr",
            file_out,
        ],
        check=True,
    )  # fmt: skip

    os.remove(file_video1)
    os.remove(file_video2)
    os.remove(file_txt)


write_video(2, 5)
write_video(5, 2)


# result = sp.run(
#     [
#         "ffprobe",
#         "-v", "error",
#         "-select_streams", "v:0",
#         "-show_frames",
#         "-show_entries",
#         "frame=best_effort_timestamp_time,pkt_pts_time,pkt_dts_time,pict_type",
#         "-of", "csv=p=0",
#         file_out,
#     ],
#     check=True,
#     capture_output=True,
#     text=True,
# )  # fmt: skip
#
# print(result.stdout)
